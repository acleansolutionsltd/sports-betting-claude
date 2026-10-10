# 🎯 Sports Betting Claude

> A Claude Project skill system that turns "what bet should I make today?" into a structured, data-driven answer.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Claude Compatible](https://img.shields.io/badge/Claude-Project%20Skills-orange)](https://claude.ai)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)

---

## What this is

A collection of **skill files** designed to be loaded into a [Claude Project](https://support.anthropic.com/en/articles/9517075-what-are-projects). Once set up, you can ask Claude a single question:

> *"What bet should I make today?"*

And get a structured answer: sport, market, line, book, stake size in units, EV%, confidence tier, and reasoning — every time.

The system is built around five layers that mirror how professional bettors think:

```
Data Ingestion → Edge Detection → Bankroll Sizing → Sport Context → Output
```

---

## ⚡ Quick start (5 minutes)

### 1. Clone the repo

```bash
git clone https://github.com/YOUR_USERNAME/sports-betting-claude.git
cd sports-betting-claude
```

### 2. Create a Claude Project

1. Go to [claude.ai](https://claude.ai) → click **Projects** in the sidebar
2. Click **New project**
3. Name it something like `Sports Betting System`

### 3. Add the skill files to your Project

In your Claude Project, open **Project instructions** and paste the contents of [`PROJECT_INSTRUCTIONS.md`](PROJECT_INSTRUCTIONS.md).

Then upload these files to your Project's **knowledge base** (drag and drop or click "Add content"):

**Start with these core files:**
- `skills/data-ingestion/SKILL.md`
- `skills/edge-detection/SKILL.md`
- `skills/bankroll-management/SKILL.md`
- `skills/performance-tracking/SKILL.md`
- `skills/shared/anti-bias-checklist.md`
- `skills/shared/output-format.md`

**Then add the sports you bet on:**
- `skills/sport-specific/nfl/SKILL.md`
- `skills/sport-specific/nba/SKILL.md`
- `skills/sport-specific/mlb/SKILL.md`
- `skills/sport-specific/nhl/SKILL.md`
- `skills/sport-specific/ncaa/SKILL.md`
- `skills/sport-specific/epl/SKILL.md`

### 4. Set your bankroll in the Project instructions

Edit the `PROJECT_INSTRUCTIONS.md` you pasted and fill in:
```
BANKROLL: $[your starting bankroll]
UNIT SIZE: $[bankroll × 0.02] (we recommend 2% per unit)
BOOKS AVAILABLE: [list the sportsbooks you have accounts with]
```

### 5. Ask your first question

Start a new conversation in the Project and type:

> **"What bet should I make today?"**

---

## 📁 Repo structure

```
sports-betting-claude/
├── README.md                          ← you are here
├── PROJECT_INSTRUCTIONS.md            ← paste this into Claude Project settings
├── LICENSE
├── CONTRIBUTING.md
│
├── skills/
│   ├── data-ingestion/
│   │   └── SKILL.md                   ← how Claude fetches lines, injuries, news
│   │
│   ├── edge-detection/
│   │   └── SKILL.md                   ← EV calculation, vig removal, edge threshold
│   │
│   ├── bankroll-management/
│   │   └── SKILL.md                   ← Kelly criterion, unit sizing, stop-loss rules
│   │
│   ├── sport-specific/
│   │   ├── nfl/SKILL.md
│   │   ├── nba/SKILL.md
│   │   ├── mlb/SKILL.md
│   │   ├── nhl/SKILL.md
│   │   ├── ncaa/SKILL.md
│   │   └── epl/SKILL.md               ← Premier League (3-way markets)
│   │
│   ├── performance-tracking/
│   │   └── SKILL.md                   ← bet log format, ROI tracking, calibration
│   │
│   └── shared/
│       ├── anti-bias-checklist.md     ← cognitive bias detection
│       └── output-format.md           ← standardized bet slip format
│
├── docs/
│   ├── how-edge-detection-works.md
│   ├── kelly-criterion-explained.md
│   ├── reading-line-movement.md
│   └── glossary.md
│
└── examples/
    ├── sample-daily-output.md          ← example of what Claude returns
    ├── sample-bet-log.md
    └── sample-bankroll-tracker.md
```

---

## 📊 What a daily output looks like

```
📅 DATE: [Today]
🏦 BANKROLL: $2,450 | UNIT: $49

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🔵 BET #1 — HIGH CONFIDENCE (4 units)
Sport:    NBA
Market:   Spread
Pick:     Celtics -4.5
Book:     DraftKings (best available)
Line:     -110
Stake:    $196
EV:       +4.2%
Reasoning: Sharp reverse line movement from -5.5 to -4.5 despite 68% public on
           Boston. Tatum O/U minutes reduced, suggesting precautionary rest
           management — load still expected. Closing line target: -5.

🟡 BET #2 — MEDIUM CONFIDENCE (2 units)
Sport:    MLB
Market:   Total (Over)
Pick:     Cubs/Cardinals O8.5
Book:     FanDuel
Line:     -115
Stake:    $98
EV:       +2.1%
Reasoning: Wrigley day game, wind blowing out 12mph to left-center. Both starters
           have struggled in day games (ERA 0.8 pts higher). Park factor elevated.

⛔ PASS: 4 other games reviewed, no qualifying edge found today.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 LOG THESE: [format for your bet log]
```

---

## 🔬 How the edge detection works

Every bet goes through this filter before Claude will recommend it:

```
1. Find the true line (best available across books, no vig)
2. Calculate implied probability from your model
3. Compare: if your P(win) > market P(win) + 2% threshold → edge exists
4. Apply Kelly: stake = (edge × bankroll) / odds
5. Reality-check against sport-specific context (Layer 4)
6. Run anti-bias checklist (Layer 5)
7. Output or discard
```

No edge = no bet. The system will explicitly tell you when to pass.

---

## ⚠️ Honest expectations

| What this system does | What it doesn't do |
|---|---|
| Structures your research process | Guarantee winners |
| Removes emotional bias | Replace your own judgment |
| Finds positive EV opportunities | Beat every line every day |
| Tracks your real edge over time | Work without your input on bankroll/books |
| Teaches you to think like a pro | Access live odds APIs automatically |

**20% monthly bankroll growth** is achievable in winning stretches but not guaranteed month-over-month. Professional bettors average 5–10% ROI over a season. This system gives you the framework — variance is still part of sports betting.

---

## 🛠️ Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). PRs welcome for:
- New sport-specific skill files (soccer, tennis, MMA, golf)
- Better data sources
- Improved bias detection heuristics
- Community-tested prompt improvements

---

## 📜 License

MIT — use it, fork it, improve it. See [LICENSE](LICENSE).

---

## 🙋 FAQ

**Do I need Claude Pro?**
Yes. Claude Projects require a Pro or Team subscription.

**Does this place bets automatically?**
No. Claude gives you the recommendation; you place the bet manually. This is intentional — always review before acting.

**What books does this work with?**
Any book you have access to. The system compares lines across whatever books you list in your Project settings.

**How do I track my bets?**
Use the `examples/sample-bet-log.md` as a template and paste your results back into the chat so Claude can update its performance model.

**Can I add my own data sources?**
Yes — the data ingestion skill file lists the search patterns Claude uses. Fork and extend them.
