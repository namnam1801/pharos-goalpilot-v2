# Pharos GoalPilot v2 - AI Financial Planner

> **"Tell me the goal. I'll figure out the transactions."**

GoalPilot v2 is an AI-powered financial planning skill for the Pharos ecosystem.  
Unlike command-based tools that require users to know *what to do*, GoalPilot starts by understanding *who you are* - then builds a personalized, simulated action plan.

---

## 🧠 What Makes GoalPilot v2 Different

Most DeFi skills are command-executors: "swap X for Y", "stake Z".

GoalPilot v2 is a **financial intelligence loop**:

```
WalletDNA          →  AI understands WHO you are
Goal Parser        →  AI understands WHAT you want
Wallet Analyzer    →  AI knows your current state
Planner Engine     →  AI generates ranked action plans
Strategy Simulator →  AI shows you WHAT WILL HAPPEN before you act
Confirmation Gate  →  You confirm → TX payloads returned
```

This is the only Pharos skill that builds a behavioral memory of your wallet before making any recommendation.

---

## ✨ Core Modules

### 🧬 WalletDNA
Analyzes on-chain history to build a wallet personality profile:

```
Wallet Type      : Yield Farmer
Risk Score       : 54/100
Behavior Score   : 82/100
Favorite Protocol: Harbor
Activity Pattern : Weekly

── Behavioral Timeline ──────────────────────
  3 months ago:  Degen Trader      Risk 81  (47 txs)
  Last month:    Yield Farmer      Risk 54  (61 txs)
  Now:           Conservative      Risk 23  (35 txs)

Trend: De-risking over time.
```

### 🎯 Goal Parser
Understands natural language financial goals:

| You say | GoalPilot understands |
|---|---|
| "I want 500 USDT by tomorrow" | `{type: liquidity, target: 500 USDT, timeframe: 1d}` |
| "Reduce my portfolio risk" | `{type: risk_reduction, risk_pref: low}` |
| "Earn yield with low risk" | `{type: yield, risk_pref: low}` |
| "Maximize my APY" | `{type: maximize_apy, risk_pref: any}` |
| "Prepare for Blockwave campaign" | `{type: campaign_prep, campaign: blockwave}` |

### 📊 Strategy Simulator
Shows outcomes *before* you commit:

```
── Strategy Simulation: Plan A ──────────────────
🟢 Optimistic   Return: +4.6%   Final: $691.25   APY: 5.3%
🟡 Base         Return: +4.2%   Final: $681.00   APY: 4.2%
🔴 Pessimistic  Return: +2.1%   Final: $649.80   APY: 2.8%

Recommendation: ✅ PROCEED  (Confidence: 80/100)
```

### 🗺️ Planner Engine
Generates ranked, multi-step Pharos-native action plans using Harbor, FaroSwap, and native staking.

---

## 🚀 Quick Start

```bash
git clone https://github.com/namnam1801/pharos-goalpilot-v2
cd pharos-goalpilot-v2
pip install -r requirements.txt

# Demo mode (no wallet needed)
python src/goalpilot.py --demo --dry-run

# One-shot goal
python src/goalpilot.py --wallet 0x... --goal "I want 500 USDT by tomorrow"

# Plan only (no confirmation)
python src/goalpilot.py --wallet 0x... --goal "reduce my risk" --dry-run

# JSON output (for agent pipelines)
python src/goalpilot.py --wallet 0x... --goal "maximize APY" --dry-run --json
```

---

## 📁 Project Structure

```
pharos-goalpilot-v2/
├── src/
│   ├── goalpilot.py        ← Main orchestrator & CLI
│   ├── wallet_dna.py       ← WalletDNA: behavioral profiling
│   ├── goal_parser.py      ← Natural language → structured intent
│   ├── wallet_analyzer.py  ← Live wallet state from Pharos RPC
│   ├── planner.py          ← Ranked action plan generation
│   └── simulator.py        ← "What if" strategy simulation
├── assets/
│   └── protocols.json      ← Pharos protocol registry + APY data
├── requirements.txt
└── README.md
```

---

## 🔌 Data Sources

| Source | Purpose | Network |
|---|---|---|
| `https://atlantic.dplabs-internal.com` | Native balance, tx count, logs | Testnet |
| `https://rpc.pharos.xyz` | Native balance, tx count, logs | Mainnet |
| `https://atlantic.pharosscan.xyz` | TX history, token balances | Testnet |
| `https://pharosscan.xyz` | TX history, token balances | Mainnet |
| `trace_filter` RPC | Contract interaction analysis | Both |

Supports **Pharos Mainnet** (Chain ID 1672) and **Atlantic Testnet** (Chain ID 688689).

---

## 🔧 Supported Frameworks

- **Pharos Skill Engine** - compatible with Pharos Agent Center
- **MCP (Model Context Protocol)** - skill is stateless and JSON-in/JSON-out ready
- **Any JSON-RPC Pharos node** - no vendor lock-in

---

## 🛡️ Safety

- **Read-only by default** - no private key required for planning
- **Dry-run mode** - `--dry-run` skips confirmation gate entirely
- **Confirmation required** - user must explicitly approve before any payload is returned
- **No funds moved** - GoalPilot returns unsigned TX payloads only; signing is always the user's responsibility

---

## 📌 Notes

- Python 3.9+ required
- Dependencies: `requests`, `web3` (optional)
- `--demo` flag runs fully offline with realistic mock data
- `--json` flag outputs machine-readable result for agent pipeline integration

---

## 🏗️ Roadmap (Phase 2)

- [ ] Live Pharos protocol APY feeds
- [ ] LP position tracking (FaroSwap)
- [ ] Health factor monitoring (Harbor borrow positions)
- [ ] MCP server wrapper for Agent Center integration
- [ ] Wallet-to-wallet DNA comparison

---

## License

MIT-0 - No attribution required. Build freely.

---

*Built for Pharos Agent Carnival - Phase 1 Skill Hackathon*  
*"Reusable tools and production-grade primitives."*
