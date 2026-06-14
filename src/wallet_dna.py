"""
WalletDNA — Pharos GoalPilot v2
Builds a behavioral personality profile from on-chain history.
"""

import json
import time
import requests
from dataclasses import dataclass, asdict
from typing import Optional


PHAROS_RPC = "https://rpc.pharos.xyz"
SOCIALSCAN_API = "https://pharos.socialscan.io/api/v1"

# Known Pharos protocol contract tags
PROTOCOL_TAGS = {
    "faroswap": "FaroSwap",
    "harbor":   "Harbor",
    "pharos":   "Pharos Native",
}


@dataclass
class WalletProfile:
    address: str
    wallet_type: str          # Yield Farmer | Degen Trader | Conservative Holder | LP Provider | Newcomer
    risk_score: int           # 0–100
    behavior_score: int       # 0–100 (overall quality)
    favorite_protocol: str
    activity_pattern: str     # Daily | Weekly | Monthly | Inactive
    total_tx: int
    active_days: int
    avg_tx_value_usd: float
    top_assets: list
    behavioral_timeline: list  # [{period, type, risk}]
    summary: str


def _rpc(method: str, params: list) -> dict:
    payload = {"jsonrpc": "2.0", "id": 1, "method": method, "params": params}
    r = requests.post(PHAROS_RPC, json=payload, timeout=10)
    return r.json().get("result", {})


def _get_tx_history(address: str, limit: int = 100) -> list:
    """
    Fetch transaction history via SocialScan API.
    Falls back to trace_filter on RPC if API unavailable.
    """
    try:
        url = f"{SOCIALSCAN_API}/explorer/command_api/account/transaction"
        params = {"address": address, "page": 1, "size": limit}
        r = requests.get(url, params=params, timeout=10)
        data = r.json()
        if data.get("status") == "1":
            return data.get("data", {}).get("list", [])
    except Exception:
        pass

    # Fallback: trace_filter (limited to recent 500 blocks)
    try:
        latest_hex = _rpc("eth_blockNumber", [])
        if not latest_hex:
            return []
        latest = int(latest_hex, 16)
        from_block = hex(max(0, latest - 500))
        result = _rpc("trace_filter", [{
            "fromBlock": from_block,
            "toBlock": "latest",
            "fromAddress": [address],
        }])
        return result if isinstance(result, list) else []
    except Exception:
        return []


def _get_token_balances(address: str) -> list:
    try:
        url = f"{SOCIALSCAN_API}/explorer/command_api/account/tokenBalance"
        r = requests.get(url, params={"address": address}, timeout=10)
        data = r.json()
        if data.get("status") == "1":
            return data.get("data", [])
    except Exception:
        pass
    return []


def _classify_wallet_type(tx_list: list, risk: int) -> str:
    if not tx_list:
        return "Newcomer"
    n = len(tx_list)
    if risk >= 75:
        return "Degen Trader"
    if risk <= 30:
        return "Conservative Holder"
    # Heuristic: detect LP interactions
    lp_keywords = ["addLiquidity", "removeLiquidity", "deposit", "withdraw"]
    lp_count = sum(
        1 for tx in tx_list
        if any(k.lower() in str(tx).lower() for k in lp_keywords)
    )
    if lp_count / max(n, 1) > 0.3:
        return "LP Provider"
    if n > 50:
        return "Yield Farmer"
    return "Casual User"


def _activity_pattern(tx_list: list) -> tuple[str, int]:
    """Returns (pattern_label, active_days_count)."""
    if not tx_list:
        return "Inactive", 0
    timestamps = []
    for tx in tx_list:
        ts = tx.get("timeStamp") or tx.get("timestamp") or tx.get("blockTime")
        if ts:
            try:
                timestamps.append(int(ts))
            except Exception:
                pass
    if not timestamps:
        return "Unknown", 0

    timestamps.sort()
    days = set(t // 86400 for t in timestamps)
    active_days = len(days)
    span_days = max((timestamps[-1] - timestamps[0]) // 86400, 1)
    freq = active_days / span_days

    if freq >= 0.7:
        return "Daily", active_days
    if freq >= 0.2:
        return "Weekly", active_days
    if freq >= 0.05:
        return "Monthly", active_days
    return "Rare", active_days


def _build_behavioral_timeline(tx_list: list) -> list:
    """
    Split tx history into 3 time buckets and assign personality per period.
    Returns list of {period, wallet_type, risk, tx_count}.
    """
    if not tx_list:
        return []

    timestamps = []
    for tx in tx_list:
        ts = tx.get("timeStamp") or tx.get("timestamp") or tx.get("blockTime")
        if ts:
            try:
                timestamps.append((int(ts), tx))
            except Exception:
                pass

    if not timestamps:
        return []

    timestamps.sort(key=lambda x: x[0])
    n = len(timestamps)
    buckets = [
        ("3 months ago", timestamps[:n//3]),
        ("Last month",   timestamps[n//3: 2*n//3]),
        ("Now",          timestamps[2*n//3:]),
    ]

    timeline = []
    for label, bucket in buckets:
        if not bucket:
            continue
        txs = [b[1] for b in bucket]
        risk = _estimate_risk(txs)
        wtype = _classify_wallet_type(txs, risk)
        timeline.append({
            "period": label,
            "wallet_type": wtype,
            "risk": risk,
            "tx_count": len(txs),
        })

    return timeline


def _estimate_risk(tx_list: list) -> int:
    """
    Simple heuristic risk score 0–100.
    High tx frequency + large values + DeFi interactions → higher risk.
    """
    if not tx_list:
        return 10
    n = len(tx_list)
    risk = min(n * 2, 40)  # volume component

    # Value component
    values = []
    for tx in tx_list:
        v = tx.get("value") or tx.get("amount") or "0"
        try:
            values.append(int(str(v), 16) if str(v).startswith("0x") else float(v))
        except Exception:
            pass
    if values:
        avg_val = sum(values) / len(values)
        risk += min(int(avg_val / 1e18 * 10), 30)  # ETH-scale

    # Interaction complexity
    contract_calls = sum(
        1 for tx in tx_list
        if tx.get("input", "0x") not in ("0x", "", None)
        or tx.get("contractAddress")
    )
    risk += min(int(contract_calls / max(n, 1) * 30), 30)

    return min(risk, 100)


def _behavior_score(tx_count: int, active_days: int, risk: int) -> int:
    """
    Composite quality score 0–100.
    Rewards consistent activity and moderate risk.
    """
    activity_score = min(tx_count * 1.5, 40)
    consistency_score = min(active_days * 2, 30)
    risk_balance = 30 - abs(risk - 50) // 3  # sweet spot around 50
    return int(min(activity_score + consistency_score + max(risk_balance, 0), 100))


def _favorite_protocol(tx_list: list) -> str:
    counts = {}
    for tx in tx_list:
        to = str(tx.get("to") or tx.get("toAddress") or "").lower()
        for key, name in PROTOCOL_TAGS.items():
            if key in to:
                counts[name] = counts.get(name, 0) + 1
    if not counts:
        return "Unknown"
    return max(counts, key=counts.get)


def _top_assets(balances: list, max_items: int = 3) -> list:
    assets = []
    for b in balances:
        symbol = b.get("symbol") or b.get("tokenSymbol", "?")
        raw = b.get("balance") or b.get("tokenBalance") or "0"
        try:
            amount = float(raw) / (10 ** int(b.get("decimals", 18)))
        except Exception:
            amount = 0.0
        assets.append({"symbol": symbol, "amount": round(amount, 4)})
    assets.sort(key=lambda x: x["amount"], reverse=True)
    return assets[:max_items]


def _build_summary(profile: dict) -> str:
    tl = profile.get("behavioral_timeline", [])
    trend = ""
    if len(tl) >= 2:
        old_risk = tl[0]["risk"]
        new_risk = tl[-1]["risk"]
        if new_risk < old_risk - 15:
            trend = " Trend: De-risking over time."
        elif new_risk > old_risk + 15:
            trend = " Trend: Increasing risk appetite."
        else:
            trend = " Trend: Consistent behavior."

    return (
        f"{profile['wallet_type']} with {profile['activity_pattern']} activity pattern. "
        f"Risk {profile['risk_score']}/100, Behavior Score {profile['behavior_score']}/100."
        f"{trend}"
    )


def analyze(address: str, demo: bool = False) -> WalletProfile:
    """
    Main entry point. Returns a WalletProfile for the given address.
    Set demo=True for deterministic mock output (no network calls).
    """
    if demo:
        return WalletProfile(
            address=address,
            wallet_type="Yield Farmer",
            risk_score=54,
            behavior_score=82,
            favorite_protocol="Harbor",
            activity_pattern="Weekly",
            total_tx=143,
            active_days=38,
            avg_tx_value_usd=124.5,
            top_assets=[
                {"symbol": "PHRS", "amount": 320.0},
                {"symbol": "USDT", "amount": 180.0},
                {"symbol": "WETH", "amount": 0.42},
            ],
            behavioral_timeline=[
                {"period": "3 months ago", "wallet_type": "Degen Trader",       "risk": 81, "tx_count": 47},
                {"period": "Last month",   "wallet_type": "Yield Farmer",        "risk": 54, "tx_count": 61},
                {"period": "Now",          "wallet_type": "Conservative Holder", "risk": 23, "tx_count": 35},
            ],
            summary=(
                "Yield Farmer with Weekly activity pattern. "
                "Risk 54/100, Behavior Score 82/100. "
                "Trend: De-risking over time."
            ),
        )

    # Live analysis
    print(f"[WalletDNA] Fetching data for {address}...")
    tx_list = _get_tx_history(address)
    balances = _get_token_balances(address)

    risk = _estimate_risk(tx_list)
    pattern, active_days = _activity_pattern(tx_list)
    wallet_type = _classify_wallet_type(tx_list, risk)
    timeline = _build_behavioral_timeline(tx_list)
    top = _top_assets(balances)
    b_score = _behavior_score(len(tx_list), active_days, risk)
    fav = _favorite_protocol(tx_list)

    # Avg tx value (rough)
    values = []
    for tx in tx_list:
        v = tx.get("value") or "0"
        try:
            values.append(int(str(v), 16) / 1e18 if str(v).startswith("0x") else float(v) / 1e18)
        except Exception:
            pass
    avg_val = round(sum(values) / max(len(values), 1) * 2000, 2)  # rough USD

    profile_dict = dict(
        address=address,
        wallet_type=wallet_type,
        risk_score=risk,
        behavior_score=b_score,
        favorite_protocol=fav,
        activity_pattern=pattern,
        total_tx=len(tx_list),
        active_days=active_days,
        avg_tx_value_usd=avg_val,
        top_assets=top,
        behavioral_timeline=timeline,
        summary="",
    )
    profile_dict["summary"] = _build_summary(profile_dict)
    return WalletProfile(**profile_dict)


def format_output(profile: WalletProfile) -> str:
    tl_lines = ""
    for t in profile.behavioral_timeline:
        tl_lines += f"  {t['period']:>15}:  {t['wallet_type']:<22} Risk {t['risk']:>3}  ({t['tx_count']} txs)\n"

    assets_str = "  " + ",  ".join(
        f"{a['symbol']}: {a['amount']}" for a in profile.top_assets
    ) if profile.top_assets else "  N/A"

    return f"""
╔══════════════════════════════════════════════════════╗
║              PHAROS  WALLET DNA                      ║
╚══════════════════════════════════════════════════════╝

  Address          : {profile.address[:10]}...{profile.address[-6:]}
  Wallet Type      : {profile.wallet_type}
  Risk Score       : {profile.risk_score}/100
  Behavior Score   : {profile.behavior_score}/100
  Fav Protocol     : {profile.favorite_protocol}
  Activity Pattern : {profile.activity_pattern}
  Total Txs        : {profile.total_tx}   Active Days: {profile.active_days}
  Avg Tx Value     : ~${profile.avg_tx_value_usd}

  Top Assets:
{assets_str}

  ── Behavioral Timeline ──────────────────────────────
{tl_lines}
  Summary: {profile.summary}
══════════════════════════════════════════════════════
"""


if __name__ == "__main__":
    import sys
    addr = sys.argv[1] if len(sys.argv) > 1 else "0xDEMO"
    demo = "--demo" in sys.argv or addr == "0xDEMO"
    profile = analyze(addr, demo=demo)
    print(format_output(profile))
