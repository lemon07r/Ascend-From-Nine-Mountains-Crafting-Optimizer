### Ascend From Nine Mountains Crafting Optimizer

A Python tool that finds the best skill rotation for the Ascend From Nine Mountains crafting system. It helps you maximize both completion and perfection bars before running out of stability.

---

### What This Does

In the game, crafting involves using skills that cost resources (Qi and Stability) to build up Completion and Perfection. Your final score is whichever bar is lower, so you need to balance both.

This optimizer:
- Finds the mathematically best rotation of skills
- Lets you play along with the game in real-time with turn-by-turn suggestions
- Accounts for the random control conditions the game throws at you

---

### Requirements

- Python 3 (no extra packages needed)

---

### Quick Start

**Find the optimal rotation:**
```bash
python3 wuxia_crafting_optimizer.py
```

This runs an exhaustive search and shows you the best possible skill sequence. With default stats, it achieves a score of 76.

**Play along with the game (interactive mode):**
```bash
python3 wuxia_crafting_optimizer.py --interactive
```

This is the most useful mode. Each turn:
1. Enter the control forecast from the game (4 numbers like `1.5,1,0.5,1`)
2. Get a suggested action
3. Press Enter to accept, or type a skill name/number to pick something else

---

### Interactive Mode Commands

| Command | What it does |
|---------|--------------|
| Enter | Accept the suggested skill |
| `1-8` | Pick a skill by its number |
| `undo` or `u` | Go back one turn |
| `status` or `s` | Show detailed progress |
| `help` or `h` | Show help |
| `quit` or `q` | Exit |

---

### Control Forecast Values

The game shows you upcoming control conditions. Enter them as 4 comma-separated numbers:

- `1.5` means +50% control
- `1.0` means normal (no change)
- `0.5` means -50% control

Example: `1.5,1,0.5,1` means this turn has +50%, next turn is normal, then -50%, then normal.

---

### Using Custom Stats

If your character has different stats, create or edit `config.json`:

```json
{
  "stats": {
    "max_qi": 194,
    "max_stability": 60,
    "base_intensity": 12,
    "base_control": 16,
    "min_stability": 10
  },
  "skills": {
    ...
  }
}
```

Then run with:
```bash
python3 wuxia_crafting_optimizer.py --config config.json
```

A default `config.json` is included in the project. You can copy and modify it for your character.

---

### Available Skills

| Skill | Qi Cost | Stability | Effect |
|-------|---------|-----------|--------|
| Simple Fusion | 0 | -10 | +12 Completion |
| Energised Fusion | 10 | -10 | +21 Completion |
| Cycling Fusion | 10 | -10 | +9 Completion, grants Control buff |
| Disciplined Touch | 10 | -10 | +6 Completion, +6 Perfection (scales with Intensity) |
| Cycling Refine | 10 | -10 | +12 Perfection, grants Intensity buff |
| Simple Refine | 18 | -10 | +16 Perfection (scales with Control) |
| Forceful Stabilize | 88 | +40 | Restores stability |
| Instant Restoration | 44 | +15 | Restores stability |

---

### How the Game Works

**Resources:**
- **Qi** (max 194): Most skills cost Qi
- **Stability** (max 60): Each action costs 10 stability. You must restore before dropping below 10.

**Goals:**
- **Completion**: Build this up with fusion skills
- **Perfection**: Build this up with refine skills
- **Score**: The lower of the two (so balance matters)

**Buffs:**
- Cycling skills grant a 40% buff to either Control or Intensity
- Buffs last 2 turns and apply to skills used on subsequent turns (not the turn you cast them)

---

### Example Session

```
$ python3 wuxia_crafting_optimizer.py --interactive

══════════════════════════════════════════════════════════════════════
                         INTERACTIVE CRAFTING
══════════════════════════════════════════════════════════════════════

  Type 'help' for commands, 'quit' to exit.

────────────────────────────────────────────────────────────────────────
  TURN 1
────────────────────────────────────────────────────────────────────────
  Qi:         194/194  ████████████████████████████████████████
  Stability:   60/60   ████████████████████████████████████████
  Completion:   0      ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░
  Perfection:   0      ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░

► Forecast (e.g. '1.5,1,0.5,1') [Enter=default]: 1,1,1,1
  Forecast: T0: normal │ T1: normal │ T2: normal │ T3: normal

  ┌──────────────────────────────────────────────────┐
  │ SUGGESTED: Energised Fusion                      │
  │   -10 Qi, -10 Stab, +21 Comp                     │
  └──────────────────────────────────────────────────┘

► Select skill [Enter=accept suggestion]: 
```

---

### All Command Line Options

```bash
# Find optimal rotation (default)
python3 wuxia_crafting_optimizer.py

# Interactive mode
python3 wuxia_crafting_optimizer.py --interactive

# Get suggestion for a specific forecast
python3 wuxia_crafting_optimizer.py --suggest-next --forecast-control '1.5,1,0.5,1'

# Use custom config file
python3 wuxia_crafting_optimizer.py --config config.json

# Show help
python3 wuxia_crafting_optimizer.py --help
```

---

### Troubleshooting

**"No valid action found"**
- Your stability is too low. You need to restore before it drops below 10.
- Or you don't have enough Qi for any skill.

**Score is lower than expected**
- Make sure you're entering the control forecast correctly (current turn first).
- Buffs from cycling skills don't apply until the next turn.

---

### Files

- `wuxia_crafting_optimizer.py` - The main script
- `config.json` - Default configuration (stats and skills)
- `AGENTS.md` - Technical documentation for developers
- `README.md` - This file

---

### License

This project is provided as-is for personal use.
