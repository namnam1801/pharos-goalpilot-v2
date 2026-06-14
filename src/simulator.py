"""
Strategy Simulator — Pharos GoalPilot v2
Simulates "what if" scenarios for each plan before user confirms.
"""

from dataclasses import dataclass
from typing import List


@dataclass
class Scenario:
    label: str          # optimistic | base | pessimistic
    return_pct: float
    final_value_usd: float
    risk_after: int
    apy: float
    notes: str


@dataclass
class SimulationResult:
    plan_id: str
    plan_summary: str
    scenarios: List[Scenario]
    recommendation: str   # PROCEED | WAIT | ADJUST
    confidence: int       # 0–100


# Protocol yield assumptions (mock; replace with live API in prod)
PROTOCOL_YIELDS = {
    "harbor":   {"base_apy": 4.2,  "risk_delta": +10, "volatility": 0.08},
    "faroswap": {"base_apy": 12.5, "risk_delta": +20, "volatility": 0.18},
    "hold":     {"base_apy": 0.0,  "risk_delta": -15, "volatility": 0.02},
    "swap":     {"base_apy": 0.0,  "risk_delta": 0,   "volatility": 0.05},
    "lp":       {"base_apy": 18.0, "risk_delta": +25, "volatility": 0.25},
}


def _detect_action_type(step: str) -> str:
    step_lower = step.lower()
    if "swap" in step_lower:
        return "swap"
    if "deposit" in step_lower or "lend" in step_lower:
        return "harbor"
    if "pool" in step_lower or "lp" in step_lower or "liquidity" in step_lower:
        return "lp"
    if "borrow" in step_lower:
        return "faroswap"
    return "hold"


def simulate(
    plan_id: str,
    plan_steps: list,
    current_value_usd: float,
    current_risk: int,
    timeframe_days: int = 30,
) -> SimulationResult:
    """
    Simulate 3 scenarios for a given plan.

    Args:
        plan_id: "A" | "B" | "C"
        plan_steps: list of step description strings
        current_value_usd: total portfolio value in USD
        current_risk: current risk score 0–100
        timeframe_days: horizon for APY calculation
    """
    # Aggregate action types from steps
    actions = [_detect_action_type(s) for s in plan_steps]
    base_apy = sum(PROTOCOL_YIELDS.get(a, PROTOCOL_YIELDS["hold"])["base_apy"] for a in actions) / max(len(actions), 1)
    risk_delta = sum(PROTOCOL_YIELDS.get(a, PROTOCOL_YIELDS["hold"])["risk_delta"] for a in actions)
    volatility = max(PROTOCOL_YIELDS.get(a, PROTOCOL_YIELDS["hold"])["volatility"] for a in actions)

    new_risk = max(0, min(100, current_risk + risk_delta))
    period_return = base_apy * (timeframe_days / 365)

    scenarios = [
        Scenario(
            label="Optimistic",
            return_pct=round(period_return * (1 + volatility), 2),
            final_value_usd=round(current_value_usd * (1 + period_return * (1 + volatility) / 100), 2),
            risk_after=max(0, new_risk - 5),
            apy=round(base_apy * (1 + volatility * 0.5), 2),
            notes="Market conditions favorable, protocol yields above average.",
        ),
        Scenario(
            label="Base",
            return_pct=round(period_return, 2),
            final_value_usd=round(current_value_usd * (1 + period_return / 100), 2),
            risk_after=new_risk,
            apy=round(base_apy, 2),
            notes="Expected market conditions, protocol yields as estimated.",
        ),
        Scenario(
            label="Pessimistic",
            return_pct=round(period_return * (1 - volatility * 2), 2),
            final_value_usd=round(current_value_usd * (1 + period_return * (1 - volatility * 2) / 100), 2),
            risk_after=min(100, new_risk + 10),
            apy=round(base_apy * (1 - volatility), 2),
            notes="Market downturn or protocol underperformance.",
        ),
    ]

    # Recommendation logic
    if new_risk > 80:
        recommendation = "WAIT"
        confidence = 35
    elif new_risk > 60 and base_apy < 5:
        recommendation = "ADJUST"
        confidence = 55
    elif base_apy > 0 and new_risk <= 60:
        recommendation = "PROCEED"
        confidence = 80
    else:
        recommendation = "PROCEED"
        confidence = 65

    plan_summary = " → ".join(plan_steps[:3])
    if len(plan_steps) > 3:
        plan_summary += f" (+{len(plan_steps)-3} more)"

    return SimulationResult(
        plan_id=plan_id,
        plan_summary=plan_summary,
        scenarios=scenarios,
        recommendation=recommendation,
        confidence=confidence,
    )


def format_simulation(result: SimulationResult) -> str:
    lines = [
        f"\n  ── Strategy Simulation: Plan {result.plan_id} ──────────────────",
        f"  Plan: {result.plan_summary}\n",
    ]
    icons = {"Optimistic": "🟢", "Base": "🟡", "Pessimistic": "🔴"}
    for s in result.scenarios:
        sign = "+" if s.return_pct >= 0 else ""
        lines.append(
            f"  {icons[s.label]} {s.label:<12} "
            f"Return: {sign}{s.return_pct:.1f}%  "
            f"Final: ${s.final_value_usd:,.2f}  "
            f"Risk: {s.risk_after}  APY: {s.apy:.1f}%"
        )
        lines.append(f"              → {s.notes}")

    rec_icon = {"PROCEED": "✅", "WAIT": "⏸️", "ADJUST": "⚠️"}
    lines.append(
        f"\n  Recommendation: {rec_icon.get(result.recommendation, '')} "
        f"{result.recommendation}  (Confidence: {result.confidence}/100)"
    )
    lines.append("  " + "─" * 54)
    return "\n".join(lines)


if __name__ == "__main__":
    # Quick demo
    result = simulate(
        plan_id="A",
        plan_steps=["Swap 200 PHRS → USDT", "Deposit 100 USDT → Harbor"],
        current_value_usd=680.0,
        current_risk=54,
        timeframe_days=30,
    )
    print(format_simulation(result))
