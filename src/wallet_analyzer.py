"""
Wallet Analyzer — Pharos GoalPilot v2
Fetches live wallet state from Pharos RPC + SocialScan.
"""

import requests
from dataclasses import dataclass
from typing import List


PHAROS_RPC = "https://rpc.pharos.xyz"
SOCIALSCAN_API = "https://pharos.socialscan.io/api/v1"

# Mock token prices (replace with live oracle in prod)
TOKEN_PRICES_USD = {
    "PHRS": 0.50,
    "USDT": 1.00,
    "USDC": 1.00,
    "WETH": 2000.0,
    "WBTC": 40000.0,
}


@dataclass
class TokenBalance:
    symbol: str
    amount: float
    value_usd: float
    is_idle: bool  # not earning yield


@dataclass
class WalletSnapshot:
    address: str
    native_phrs: float
    native_usd: float
    tokens: List[TokenBalance]
    total_usd: float
    idle_usd: float
    risk_score: int
    lp_positions: list


def _rpc(method: str, params: list):
    r = requests.post(PHAROS_RPC, json={
        "jsonrpc": "2.0", "id": 1, "method": method, "params": params
    }, timeout=10)
    return r.json().get("result")


def _get_native_balance(address: str) -> float:
    try:
        result = _rpc("eth_getBalance", [address, "latest"])
        if result:
            return int(result, 16) / 1e18
    except Exception:
        pass
    return 0.0


def _get_token_balances(address: str) -> list:
    try:
        r = requests.get(
            f"{SOCIALSCAN_API}/explorer/command_api/account/tokenBalance",
            params={"address": address}, timeout=10
        )
        data = r.json()
        if data.get("status") == "1":
            return data.get("data", [])
    except Exception:
        pass
    return []


def _get_lp_positions(address: str) -> list:
    """Stub — query known LP contracts for position data."""
    return []


def snapshot(address: str, demo: bool = False) -> WalletSnapshot:
    if demo:
        tokens = [
            TokenBalance("USDT", 180.0, 180.0, True),
            TokenBalance("WETH", 0.042, 84.0, True),
        ]
        return WalletSnapshot(
            address=address,
            native_phrs=320.0,
            native_usd=160.0,
            tokens=tokens,
            total_usd=424.0,
            idle_usd=244.0,
            risk_score=54,
            lp_positions=[],
        )

    print(f"[WalletAnalyzer] Fetching wallet state for {address}...")
    native = _get_native_balance(address)
    native_usd = native * TOKEN_PRICES_USD.get("PHRS", 0.5)

    raw_tokens = _get_token_balances(address)
    tokens: List[TokenBalance] = []
    for t in raw_tokens:
        symbol = t.get("symbol") or t.get("tokenSymbol", "?")
        decimals = int(t.get("decimals", 18))
        raw_amt = t.get("balance") or t.get("tokenBalance") or "0"
        try:
            amount = float(raw_amt) / (10 ** decimals)
        except Exception:
            amount = 0.0
        price = TOKEN_PRICES_USD.get(symbol.upper(), 0.0)
        value_usd = amount * price
        tokens.append(TokenBalance(
            symbol=symbol,
            amount=round(amount, 4),
            value_usd=round(value_usd, 2),
            is_idle=True,  # simplified — no LP check yet
        ))

    lp_positions = _get_lp_positions(address)
    total_usd = native_usd + sum(t.value_usd for t in tokens)
    idle_usd = native_usd + sum(t.value_usd for t in tokens if t.is_idle)

    # Simple risk: ratio of volatile assets
    volatile_usd = native_usd + sum(
        t.value_usd for t in tokens
        if t.symbol.upper() not in ("USDT", "USDC", "DAI")
    )
    risk_score = min(int(volatile_usd / max(total_usd, 1) * 100), 100)

    return WalletSnapshot(
        address=address,
        native_phrs=round(native, 4),
        native_usd=round(native_usd, 2),
        tokens=tokens,
        total_usd=round(total_usd, 2),
        idle_usd=round(idle_usd, 2),
        risk_score=risk_score,
        lp_positions=lp_positions,
    )


def format_snapshot(w: WalletSnapshot) -> str:
    lines = [
        f"\n  Wallet Snapshot  ({w.address[:10]}...{w.address[-6:]})",
        f"  PHRS (native) : {w.native_phrs}  (~${w.native_usd})",
    ]
    for t in w.tokens:
        lines.append(f"  {t.symbol:<12}: {t.amount}  (~${t.value_usd})")
    lines += [
        f"  ─────────────────────────────",
        f"  Total Value   : ${w.total_usd}",
        f"  Idle Assets   : ${w.idle_usd}  (not earning)",
        f"  Risk Score    : {w.risk_score}/100",
    ]
    return "\n".join(lines)
