"""
Goal Parser — Pharos GoalPilot v2
Parses natural language goals into structured intent.
"""

import re
from dataclasses import dataclass
from typing import Optional


@dataclass
class ParsedGoal:
    raw: str
    goal_type: str        # yield | liquidity | risk_reduction | campaign_prep | maximize_apy | unknown
    target_amount: Optional[float]
    target_asset: Optional[str]
    timeframe_days: Optional[int]
    risk_preference: str  # low | medium | high | any
    campaign: Optional[str]


GOAL_PATTERNS = [
    (r"(earn|get|yield|generate).*(low|safe|stable)", "yield", "low"),
    (r"(maximize|max|best).*(apy|yield|return)", "maximize_apy", "high"),
    (r"(reduce|lower|decrease|cut).*(risk|exposure)", "risk_reduction", "low"),
    (r"(prepare|ready|setup).*(campaign|blockwave|event)", "campaign_prep", "medium"),
    (r"(want|need|get|have)\s+\d+.*\b(usdt|usdc|usd|eth|phrs)\b", "liquidity", "medium"),
    (r"(want|need)\s+(some\s+)?(cash|liquidity|stable)", "liquidity", "medium"),
    (r"(swap|convert|exchange)", "liquidity", "medium"),
    (r"(stake|staking)", "yield", "medium"),
    (r"(earn|yield|passive)", "yield", "medium"),
]

TIMEFRAME_MAP = {
    "today": 1, "tomorrow": 1, "day": 1,
    "week": 7, "month": 30, "year": 365,
    "hour": 1,
}

ASSET_PATTERNS = ["usdt", "usdc", "phrs", "weth", "eth", "wbtc", "btc"]


def parse(goal_text: str) -> ParsedGoal:
    text = goal_text.lower().strip()

    # Detect goal type
    goal_type = "unknown"
    risk_pref = "medium"
    for pattern, g_type, risk in GOAL_PATTERNS:
        if re.search(pattern, text):
            goal_type = g_type
            risk_pref = risk
            break

    # Detect amount
    amount_match = re.search(r"(\d[\d,]*\.?\d*)\s*(usdt|usdc|phrs|eth|usd|\$)?", text)
    target_amount = None
    target_asset = None
    if amount_match:
        try:
            target_amount = float(amount_match.group(1).replace(",", ""))
        except Exception:
            pass

    # Detect asset
    for asset in ASSET_PATTERNS:
        if asset in text:
            target_asset = asset.upper()
            break

    # Detect timeframe
    timeframe_days = None
    for keyword, days in TIMEFRAME_MAP.items():
        if keyword in text:
            timeframe_days = days
            break

    # Campaign
    campaign = None
    camp_match = re.search(r"(blockwave|campaign\s+\w+|\w+\s+campaign)", text)
    if camp_match:
        campaign = camp_match.group(1).strip()

    # Risk override from explicit mention
    if "low risk" in text or "safe" in text:
        risk_pref = "low"
    elif "high risk" in text or "aggressive" in text or "degen" in text:
        risk_pref = "high"
    elif "any" in text or "max" in text:
        risk_pref = "any"

    return ParsedGoal(
        raw=goal_text,
        goal_type=goal_type,
        target_amount=target_amount,
        target_asset=target_asset,
        timeframe_days=timeframe_days,
        risk_preference=risk_pref,
        campaign=campaign,
    )


def format_parsed(goal: ParsedGoal) -> str:
    parts = [f"  Goal Type    : {goal.goal_type}"]
    if goal.target_amount:
        parts.append(f"  Target       : {goal.target_amount} {goal.target_asset or ''}")
    if goal.timeframe_days:
        parts.append(f"  Timeframe    : {goal.timeframe_days} day(s)")
    parts.append(f"  Risk Pref    : {goal.risk_preference}")
    if goal.campaign:
        parts.append(f"  Campaign     : {goal.campaign}")
    return "\n".join(parts)


if __name__ == "__main__":
    tests = [
        "I want 500 USDT by tomorrow",
        "Reduce my portfolio risk",
        "Earn yield with low risk",
        "Maximize my APY",
        "Prepare my wallet for Blockwave campaign",
    ]
    for t in tests:
        g = parse(t)
        print(f"\n> {t}")
        print(format_parsed(g))
