# Contributing to Sports Betting Claude

Thanks for wanting to improve the system. This is a community-built tool and the best contributions come from people who've actually run these skill files against real betting markets.

---

## What we're looking for

**High value contributions:**
- New sport-specific skill files (soccer/EPL, tennis, MMA, golf, WNBA)
- Improved edge detection heuristics with documented reasoning
- Better data sources (especially free ones)
- Bug fixes — places where the skill files give contradictory or broken instructions
- Real-world test results: if a skill file gave you bad guidance, document it
- New shared utilities (e.g., a vig-removal calculator prompt, a line shopping helper)

**Not looking for:**
- "Hot picks" or specific bet recommendations
- Strategies based purely on feel or narrative
- Anything that claims guaranteed profits
- Promotions for specific sportsbooks (keep it book-agnostic)

---

## How to contribute

### 1. Fork and clone

```bash
git clone https://github.com/YOUR_USERNAME/sports-betting-claude.git
cd sports-betting-claude
git checkout -b feature/your-contribution-name
```

### 2. Make your changes

Follow the skill file format established in existing files:
- Start with a clear `# SKILL: [Name]` header
- Include a `> **Purpose:**` one-liner
- Use consistent section headers
- Include specific search queries where relevant
- Include concrete numbers and thresholds — avoid vague language like "consider" or "might"
- Include red flags and when-to-pass sections
- Test your changes in a real Claude Project before submitting

### 3. Test it

Before submitting, add your skill file(s) to a Claude Project and run at least one week of real analysis. Document what worked and what didn't in your PR.

### 4. Submit a PR

```bash
git add .
git commit -m "Add: [what you added and why]"
git push origin feature/your-contribution-name
```

Open a PR with:
- What sport/feature you're adding
- Why the current skill files are missing this
- How you tested it
- Any real-world results if available

---

## Skill file standards

### Required sections in every SKILL.md

```markdown
# SKILL: [Name]

> **Purpose:** One sentence on what this skill does.

---

## When to use this skill

## [Main content sections]

## Red flags (lean to pass)

## Key sources / Search queries
```

### Style guide

- Use concrete numbers: `+3 to +5 points` not `significant advantage`
- Use code blocks for formulas, search queries, and data structures
- Use tables for quick reference lookups
- Keep reasoning tight — every instruction should have a "why" either stated or obvious
- Sentence case everywhere (not Title Case)
- No emoji in skill files except in the output-format.md (which mirrors user output)

### Threshold decisions

If you're changing a number (e.g., adjusting the wind threshold from 15mph to 12mph), explain why in a comment above the threshold. Include what source or analysis led you there.

---

## Reporting issues

Use GitHub Issues for:
- Skill file instructions that led to a systematic mistake
- Missing sport or bet type coverage
- Contradictory instructions between two skill files
- Data source that's no longer accurate or available

Use the issue template and include the specific skill file and section causing the problem.

---

## Code of conduct

Keep discussions focused on the betting system. We're not here to argue about specific picks, debate sportsbook ethics, or discuss gambling addiction (there are better resources for that). If someone is showing signs of problem gambling in the issues/discussions, point them toward help resources and move on.

---

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
