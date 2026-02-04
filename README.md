### Ascend From Nine Mountains Crafting Optimizer

A Python tool that finds the best skill rotation for the Ascend From Nine Mountains crafting system. It helps you reach specific completion and perfection targets, or maximize both bars before running out of stability.

---

### What This Does

In the game, crafting involves using skills that cost resources (Qi and Stability) to build up Completion and Perfection. You can set specific targets for both values, and the optimizer will find the most efficient path to reach them.

This optimizer:
- Finds the mathematically best rotation of skills to reach your targets
- Lets you play along with the game in real-time with turn-by-turn suggestions
- Accounts for the random control conditions the game throws at you
- Supports both target-based optimization and legacy balanced scoring

---

### Requirements

- Python 3 (no extra packages needed)

---

### Quick Start

**Find the optimal rotation with specific targets:**
```bash
python3 wuxia_crafting_optimizer.py -t 50 50
```

This runs an exhaustive search and shows you the best skill sequence to reach your completion and perfection targets.

**Find the optimal rotation (legacy balanced mode):**
```bash
python3 wuxia_crafting_optimizer.py
```

Without targets, the optimizer maximizes `min(completion, perfection)` for a balanced score.

**Play along with the game (interactive mode):**
```bash
python3 wuxia_crafting_optimizer.py -i -t 60 60
```

This is the most useful mode. Each turn:
1. See the AI-suggested action (based on default forecast)
2. Pick a skill (press Enter to accept suggestion, or type a number/name)
3. Enter the control forecast from the game (4 numbers like `1.5,1,0.5,1`)
4. The skill is applied with your forecast
5. Session ends automatically when both targets are met

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

By default, the script will load `config.json` from the project directory (next to `wuxia_crafting_optimizer.py`) when it exists.

You can also specify a config path explicitly:
```bash
python3 wuxia_crafting_optimizer.py --config config.json
```

A default `config.json` is included in the project. You can copy and modify it for your character.

Notes:
- In `config.json`, `stability_cost > 0` means you **spend** stability (usually `10`), and `stability_cost < 0` means you **restore** stability.
- `buff_type` must be one of: `"NONE"`, `"CONTROL"`, `"INTENSITY"`.
- `Disciplined Touch` scales with your Intensity stat, so its `completion_gain` / `perfection_gain` are `0` in `config.json` by design (the gains are computed in code).

---

### Available Skills (Default Configuration)

These are the skills included in the default `config.json`. Values can be customized for your character.

| Skill | Qi Cost | Stability Cost | Effect |
|-------|---------|-----------|--------|
| Simple Fusion | 0 | 10 | +12 Completion |
| Energised Fusion | 10 | 10 | +21 Completion |
| Cycling Fusion | 10 | 10 | +9 Completion, grants Control buff |
| Disciplined Touch | 10 | 10 | +6 Completion, +6 Perfection (scales with Intensity) |
| Cycling Refine | 10 | 10 | +12 Perfection, grants Intensity buff |
| Simple Refine | 18 | 10 | +16 Perfection (scales with Control) |
| Forceful Stabilize | 88 | -40 | Restores stability |
| Instant Restoration | 44 | -15 | Restores stability |

*Note: Skill costs and effects vary based on your character's stats and configuration.*

---

### How the Game Works

**Resources:**
- **Qi**: Most skills cost Qi. Your max Qi depends on your character (default: 194).
- **Stability**: Most actions cost stability. Stability must stay at or above the minimum threshold after every action. Your max stability and minimum threshold depend on your character (defaults: max 60, min 10).

**Goals:**
- **Completion**: Build this up with fusion skills
- **Perfection**: Build this up with refine skills
- **Targets**: Set specific completion and perfection values to reach
- **Score** (legacy mode): Without targets, score = the lower of the two (so balance matters)

**Buffs:**
- Cycling skills grant buffs to either Control or Intensity (default: +40%)
- Buff duration depends on the skill configuration (default: 2 turns)
- Buffs apply to skills used on subsequent turns (not the turn you cast them)

---

### Example Session

```
$ python3 wuxia_crafting_optimizer.py --interactive

╔════════════════════════════════════════════════════════════════════╗
║          ASCEND FROM NINE MOUNTAINS - INTERACTIVE MODE             ║
╚════════════════════════════════════════════════════════════════════╝

┌────────────────────────────────────────────────────────────────────┐
│                             COMMANDS                               │
├────────────────────────────────────────────────────────────────────┤
│  Forecast: Enter 4 control multipliers (e.g. '1.5,1,0.5,1')        │
│            Press Enter for default (1,1,1,1)                       │
│                                                                    │
│  Actions:  Enter number or name to select skill                    │
│            Press Enter to accept suggestion                        │
│                                                                    │
│  Other:    'help' or 'h' - Show this help                          │
│            'undo' or 'u' - Undo last action                        │
│            'status' or 's' - Show detailed status                  │
│            'quit' or 'q' - Exit interactive mode                   │
└────────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────────┐
│                              TURN 1                                │
└────────────────────────────────────────────────────────────────────┘
  Qi: 194/194 ███████████████   Stability: 60/60 ███████████████
  Completion:   0                    Perfection:   0
  ══► SCORE: 0

  ┌──────────────────────────────────────────────────┐
  │ ★ SUGGESTED: Energised Fusion                    │
  │   -10 Qi, -10 Stab, +21 Comp                     │
  └──────────────────────────────────────────────────┘

  Available skills:
  ────────────────────────────────────────────────────────────────
   ★ 1. Energised Fusion        -10 Qi, -10 Stab, +21 Comp
     2. Simple Fusion           0 Qi, -10 Stab, +12 Comp
     ...
  ────────────────────────────────────────────────────────────────

► Select skill [Enter=accept suggestion]: 
► Forecast (e.g. '1.5,1,0.5,1') [Enter=default]: 1,1,1,1
  Forecast: T0: normal │ T1: normal │ T2: normal │ T3: normal
```

---

### All Command Line Options

| Short | Long | Description |
|-------|------|-------------|
| `-i` | `--interactive` | Interactive mode (turn-by-turn) |
| `-t` | `--targets` | Set both targets at once: `-t 60 60` |
| `-c` | `--target-completion` | Target completion value |
| `-p` | `--target-perfection` | Target perfection value |
| `-s` | `--suggest-next` | Suggest best action for forecast |
| `-f` | `--forecast-control` | Control forecast (e.g. `1.5,1,0.5,1`) |
| | `--config` | Path to custom config file |

```bash
# Find optimal rotation with targets (recommended)
python3 wuxia_crafting_optimizer.py -t 50 50

# Interactive mode with targets
python3 wuxia_crafting_optimizer.py -i -t 60 60

# Interactive mode (legacy balanced mode)
python3 wuxia_crafting_optimizer.py -i

# Get suggestion for a specific forecast with targets
python3 wuxia_crafting_optimizer.py -s -f '1.5,1,0.5,1' -t 50 50

# Legacy balanced mode (no targets)
python3 wuxia_crafting_optimizer.py

# Use custom config file
python3 wuxia_crafting_optimizer.py --config config.json -t 50 50

# Show help
python3 wuxia_crafting_optimizer.py --help
```

**Note:** Use `-t 60 60` as shorthand, or `-c 60 -p 60` for separate target flags. Both completion and perfection targets must be provided together.

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
