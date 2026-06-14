"""
Planner — Pharos GoalPilot v2
Generates ranked multi-step action plans based on goal + wallet state.
"""

from dataclasses import dataclass, field
from typing import List
from goal_parser import ParsedGoal
from wallet_analyzer import WalletSnapshot


@dataclass
class Plan:
    plan_id: str          # A | B | C
    label: str
    steps: List[str]
    score: int            # 0–100
    expected_outcome: str
    risk_after: int
    apy: float
    notes: str


def _yield_plans(goal: ParsedGoal, wallet: WalletSnapshot) -> List[Plan]:
    plans = []

    # Plan A: Safe yield via Harbor
    if wallet.idle_usd > 50:
        steps = []
        deposit_phrs = min(wallet.native_phrs * 0.5, 500)
        if deposit_phrs > 10:
            steps.append(f"Deposit {deposit_phrs:.0f} PHRS → Harbor (est. 4.2% APY)")
        if wallet.total_usd > 200:
            steps.append("Stake remaining PHRS for staking rewards")
        plans.append(Plan(
            plan_id="A",
            label="Safe Yield (Harbor)",
            steps=steps or ["Deposit PHRS → Harbor"],
            score=88,
            expected_outcome=f"~{wallet.total_usd * 0.042:.1f} USDT/year passive income",
            risk_after=max(wallet.risk_score - 10, 10),
            apy=4.2,
            notes="Lowest risk, stable yield on Pharos native protocol.",
        ))

    # Plan B: LP yield via FaroSwap
    plans.append(Plan(
        plan_id="B",
        label="LP Yield (FaroSwap PHRS/USDT)",
        steps=[
            f"Swap {wallet.native_phrs * 0.25:.0f} PHRS → USDT",
            "Add PHRS/USDT liquidity to FaroSwap pool",
            "Receive LP tokens + fee rewards",
        ],
        score=71,
        expected_outcome=f"~{wallet.total_usd * 0.125:.1f} USDT/year (12.5% APY)",
        risk_after=min(wallet.risk_score + 15, 100),
        apy=12.5,
        notes="Higher yield but exposed to impermanent loss.",
    ))

    # Plan C: Aggressive — borrow + LP
    if wallet.total_usd > 300:
        plans.append(Plan(
            plan_id="C",
            label="Leveraged Yield (Borrow + LP)",
            steps=[
                f"Deposit {wallet.native_phrs * 0.6:.0f} PHRS as collateral → Harbor",
                "Borrow 150 USDT against collateral",
                "Add PHRS/USDT LP with borrowed USDT",
                "Earn LP fees + manage health factor",
            ],
            score=52,
            expected_outcome=f"~{wallet.total_usd * 0.18:.1f} USDT/year (18%+ APY)",
            risk_after=min(wallet.risk_score + 30, 100),
            apy=18.0,
            notes="Maximum yield but requires active monitoring of health factor.",
        ))

    return plans


def _liquidity_plans(goal: ParsedGoal, wallet: WalletSnapshot) -> List[Plan]:
    target = goal.target_amount or 200
    plans = []

    # Plan A: Direct swap
    swap_phrs = min(target / 0.5, wallet.native_phrs * 0.7)
    plans.append(Plan(
        plan_id="A",
        label="Direct Swap",
        steps=[f"Swap {swap_phrs:.0f} PHRS → USDT  (est. ${swap_phrs * 0.5:.0f})"],
        score=89,
        expected_outcome=f"~${swap_phrs * 0.5:.0f} USDT immediately",
        risk_after=max(wallet.risk_score - 5, 5),
        apy=0.0,
        notes="Fastest path to liquidity. Price impact depends on pool depth.",
    ))

    # Plan B: Swap + lend remainder
    plans.append(Plan(
        plan_id="B",
        label="Swap + Lend",
        steps=[
            f"Swap {swap_phrs * 0.6:.0f} PHRS → USDT",
            f"Deposit {swap_phrs * 0.4:.0f} PHRS → Harbor to earn while holding",
        ],
        score=74,
        expected_outcome=f"~${swap_phrs * 0.3:.0f} USDT + ongoing yield",
        risk_after=wallet.risk_score,
        apy=4.2,
        notes="Partial liquidity with yield on remainder.",
    ))

    return plans


def _risk_reduction_plans(goal: ParsedGoal, wallet: WalletSnapshot) -> List[Plan]:
    return [
        Plan(
            plan_id="A",
            label="De-risk: Swap volatile → Stables",
            steps=[
                f"Swap {wallet.native_phrs * 0.4:.0f} PHRS → USDT",
                "Keep 60% PHRS exposure",
            ],
            score=85,
            expected_outcome="Risk score reduced by ~20 points",
            risk_after=max(wallet.risk_score - 20, 5),
            apy=0.0,
            notes="Reduces volatility exposure while keeping Pharos position.",
        ),
        Plan(
            plan_id="B",
            label="De-risk: Stables into Harbor",
            steps=[
                f"Swap {wallet.native_phrs * 0.5:.0f} PHRS → USDT",
                "Deposit USDT → Harbor stable pool (4.2% APY)",
            ],
            score=78,
            expected_outcome="Risk score reduced by ~25 points + stable yield",
            risk_after=max(wallet.risk_score - 25, 5),
            apy=4.2,
            notes="Best of both worlds: lower risk + passive income.",
        ),
    ]


def _campaign_prep_plans(goal: ParsedGoal, wallet: WalletSnapshot) -> List[Plan]:
    return [
        Plan(
            plan_id="A",
            label="Campaign Prep: Bridge + Position",
            steps=[
                "Ensure PHRS balance > 100 for gas",
                "Swap 30% portfolio to campaign asset",
                "Stake remaining for Pharos points",
            ],
            score=82,
            expected_outcome="Wallet ready for campaign interactions",
            risk_after=wallet.risk_score,
            apy=0.0,
            notes="Optimizes for campaign participation, not pure yield.",
        ),
    ]


PLAN_GENERATORS = {
    "yield":          _yield_plans,
    "maximize_apy":   _yield_plans,
    "liquidity":      _liquidity_plans,
    "risk_reduction": _risk_reduction_plans,
    "campaign_prep":  _campaign_prep_plans,
}


def generate_plans(goal: ParsedGoal, wallet: WalletSnapshot) -> List[Plan]:
    generator = PLAN_GENERATORS.get(goal.goal_type, _liquidity_plans)
    plans = generator(goal, wallet)
    plans.sort(key=lambda p: p.score, reverse=True)
    return plans


def format_plans(plans: List[Plan]) -> str:
    lines = []
    for plan in plans:
        bar = "─" * (45 - len(plan.label))
        lines.append(f"\n  ── Plan {plan.plan_id}: {plan.label} {bar} Score: {plan.score}")
        for i, step in enumerate(plan.steps, 1):
            lines.append(f"    Step {i}: {step}")
        lines += [
            f"    Expected   : {plan.expected_outcome}",
            f"    Risk after : {plan.risk_after}/100    APY: {plan.apy}%",
            f"    Notes      : {plan.notes}",
        ]
    return "\n".join(lines)
