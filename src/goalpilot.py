#!/usr/bin/env python3
"""
Pharos GoalPilot v2
===================
Goal-driven AI agent skill for the Pharos ecosystem.

  WalletDNA + Goal Parser + Wallet Analyzer + Planner + Simulator
  → The only Pharos skill that understands WHO you are before it plans WHAT to do.

Usage:
  python goalpilot.py --demo
  python goalpilot.py --wallet 0x... --goal "I want 500 USDT by tomorrow"
  python goalpilot.py --wallet 0x... --goal "reduce my risk" --dry-run
  python goalpilot.py --wallet 0x... --goal "earn yield" --json
"""

import sys
import json
import argparse

# Local imports
sys.path.insert(0, ".")
import wallet_dna
import wallet_analyzer
import goal_parser
import planner
import simulator


BANNER = """
╔══════════════════════════════════════════════════════════════╗
║          PHAROS  GOALPILOT  v2  //  AI Financial Planner    ║
║          Tell me the goal. I'll figure out the transactions. ║
╚══════════════════════════════════════════════════════════════╝
"""

SEPARATOR = "  " + "═" * 58


def run(wallet: str, goal_text: str, dry_run: bool = False,
        demo: bool = False, json_output: bool = False) -> dict:

    print(BANNER)

    # ── Step 1: WalletDNA ────────────────────────────────────────
    print("  [1/4] Building WalletDNA profile...\n")
    dna = wallet_dna.analyze(wallet, demo=demo)
    print(wallet_dna.format_output(dna))
    print(SEPARATOR)

    # ── Step 2: Parse Goal ───────────────────────────────────────
    print("\n  [2/4] Parsing your goal...\n")
    parsed = goal_parser.parse(goal_text)
    print(f"  Goal: \"{parsed.raw}\"")
    print(goal_parser.format_parsed(parsed))
    print(SEPARATOR)

    # ── Step 3: Wallet Snapshot ──────────────────────────────────
    print("\n  [3/4] Analyzing current wallet state...\n")
    w_snap = wallet_analyzer.snapshot(wallet, demo=demo)
    print(wallet_analyzer.format_snapshot(w_snap))
    print(SEPARATOR)

    # ── Step 4: Generate Plans ───────────────────────────────────
    print("\n  [4/4] Generating ranked action plans...\n")
    plans = planner.generate_plans(parsed, w_snap)
    print(planner.format_plans(plans))
    print(SEPARATOR)

    # ── Step 5: Simulate Top 2 Plans ─────────────────────────────
    print("\n  [5/5] Running strategy simulations...\n")
    sim_results = []
    for p in plans[:2]:
        sim_result = simulator.simulate(
            plan_id=p.plan_id,
            plan_steps=p.steps,
            current_value_usd=w_snap.total_usd,
            current_risk=w_snap.risk_score,
            timeframe_days=parsed.timeframe_days or 30,
        )
        sim_results.append(sim_result)
        print(simulator.format_simulation(sim_result))
    print(SEPARATOR)

    # ── Dry-run: stop here ───────────────────────────────────────
    if dry_run:
        print("\n  [DRY-RUN] Planning complete. No transactions will be submitted.\n")
        result = _build_result(dna, parsed, w_snap, plans, sim_results)
        if json_output:
            print(json.dumps(result, indent=2, default=str))
        return result

    # ── Confirmation Gate ─────────────────────────────────────────
    print(f"\n  ✅ Recommended: Plan {plans[0].plan_id} — {plans[0].label}")
    print(f"     {plans[0].steps[0] if plans[0].steps else ''}")
    print()
    choice = input("  Proceed with Plan A? [y/n/b/c/details]: ").strip().lower()

    if choice in ("y", "yes", "a"):
        selected = plans[0]
    elif choice == "b" and len(plans) > 1:
        selected = plans[1]
    elif choice == "c" and len(plans) > 2:
        selected = plans[2]
    elif choice == "details":
        print("\n  Full plan details printed above. Re-run to confirm.")
        return {}
    else:
        print("\n  Cancelled. No transactions submitted.\n")
        return {}

    # ── Return TX Payloads ────────────────────────────────────────
    payloads = _build_tx_payloads(selected, w_snap)
    print(f"\n  Generating transaction payloads for Plan {selected.plan_id}...\n")
    for i, payload in enumerate(payloads, 1):
        print(f"  TX {i}: {json.dumps(payload, indent=4)}")

    print("\n  ⚠️  Review each payload before signing. GoalPilot never holds private keys.\n")

    result = _build_result(dna, parsed, w_snap, plans, sim_results, selected_plan=selected, tx_payloads=payloads)
    if json_output:
        print(json.dumps(result, indent=2, default=str))
    return result


def _build_tx_payloads(plan: planner.Plan, wallet: wallet_analyzer.WalletSnapshot) -> list:
    """
    Returns unsigned transaction payload stubs.
    A real implementation would encode ABI calldata per step.
    """
    payloads = []
    for i, step in enumerate(plan.steps):
        payloads.append({
            "step": i + 1,
            "description": step,
            "from": wallet.address,
            "to": "0x<protocol_contract>",
            "value": "0x0",
            "data": "0x<encoded_calldata>",
            "chainId": 1672,
            "network": "Pharos Mainnet",
            "note": "Sign with your wallet. GoalPilot does not submit transactions."
        })
    return payloads


def _build_result(dna, parsed, w_snap, plans, sim_results,
                  selected_plan=None, tx_payloads=None) -> dict:
    return {
        "wallet_dna": {
            "wallet_type":    dna.wallet_type,
            "risk_score":     dna.risk_score,
            "behavior_score": dna.behavior_score,
            "favorite_protocol": dna.favorite_protocol,
            "activity_pattern":  dna.activity_pattern,
            "summary":        dna.summary,
        },
        "goal": {
            "raw":            parsed.raw,
            "type":           parsed.goal_type,
            "target_amount":  parsed.target_amount,
            "target_asset":   parsed.target_asset,
            "timeframe_days": parsed.timeframe_days,
            "risk_preference":parsed.risk_preference,
        },
        "wallet_snapshot": {
            "total_usd":  w_snap.total_usd,
            "idle_usd":   w_snap.idle_usd,
            "risk_score": w_snap.risk_score,
            "phrs":       w_snap.native_phrs,
        },
        "plans": [
            {
                "id":    p.plan_id,
                "label": p.label,
                "score": p.score,
                "steps": p.steps,
                "expected_outcome": p.expected_outcome,
                "risk_after": p.risk_after,
                "apy":   p.apy,
            }
            for p in plans
        ],
        "simulations": [
            {
                "plan_id":        s.plan_id,
                "recommendation": s.recommendation,
                "confidence":     s.confidence,
                "scenarios": [
                    {"label": sc.label, "return_pct": sc.return_pct,
                     "final_value_usd": sc.final_value_usd, "apy": sc.apy}
                    for sc in s.scenarios
                ],
            }
            for s in sim_results
        ],
        "selected_plan":  selected_plan.plan_id if selected_plan else None,
        "tx_payloads":    tx_payloads or [],
    }


def main():
    parser = argparse.ArgumentParser(
        description="Pharos GoalPilot v2 — AI Financial Planner for Pharos"
    )
    parser.add_argument("--wallet",  default="0xDEMO", help="Wallet address (0x...)")
    parser.add_argument("--goal",    default="",       help="Your financial goal in natural language")
    parser.add_argument("--dry-run", action="store_true", help="Plan only, no confirmation gate")
    parser.add_argument("--demo",    action="store_true", help="Demo mode (no network calls)")
    parser.add_argument("--json",    action="store_true", help="Output full result as JSON")
    args = parser.parse_args()

    wallet = args.wallet
    demo_mode = args.demo or wallet == "0xDEMO"

    goal_text = args.goal
    if not goal_text:
        if demo_mode:
            goal_text = "I want 500 USDT by tomorrow"
        else:
            print("  Enter your financial goal:")
            goal_text = input("  > ").strip()

    run(
        wallet=wallet,
        goal_text=goal_text,
        dry_run=args.dry_run,
        demo=demo_mode,
        json_output=args.json,
    )


if __name__ == "__main__":
    main()
