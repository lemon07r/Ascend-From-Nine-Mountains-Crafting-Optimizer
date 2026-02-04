# AGENTS.md - Ascend From Nine Mountains Crafting Optimizer

This document provides guidance for AI agents and developers working with the Ascend From Nine Mountains Crafting Optimizer codebase.

---

## Project Overview

**Purpose**: This script finds the optimal skill rotation for the Ascend From Nine Mountains crafting system. The goal is to reach specific completion and perfection targets, or maximize both bars before running out of stability.

**Language**: Python 3 (no external dependencies required)

**Main File**: `wuxia_crafting_optimizer.py` (~1120 lines)

---

## Game Mechanics (Critical Context)

Understanding these rules is essential for any modifications:

### Resources
| Resource | Max Value | Notes |
|----------|-----------|-------|
| Qi | 194 | Consumed by most skills |
| Stability | 60 | Consumed by actions (10 per action unless restoring) |
| Completion | ∞ | Goal metric, scales with Intensity |
| Perfection | ∞ | Goal metric, scales with Control |

### Core Rules
1. **Stability Constraint**: Stability MUST stay `>= 10` after every action. You may end a turn at exactly `10`, but then you must restore next (you cannot take another `-10` action).
2. **Scoring**: 
   - **Target Mode**: When `--target-completion` and `--target-perfection` are provided, score = sum of progress toward each target (capped at target values). Optimization stops when both targets are met.
   - **Legacy Mode**: Without targets, score = `min(completion, perfection)` — both bars must be balanced.
3. **Buff Timing**: Buffs from cycling skills apply to SUBSEQUENT turns, not the current turn.
4. **Control Conditions**: Random game conditions can modify Control by ±50% per turn.

### Rounding / Flooring
All scaling uses integer flooring/truncation (Python `int(...)` and `//`). Do not change to rounding without updating expected results.

### Stats
- **Intensity** (12): Affects completion-gaining skills
- **Control** (16): Affects perfection-gaining skills
- Buffs provide +40% to their respective stat for 2 turns

---

## Architecture

### Key Classes

#### `State` (dataclass)
Represents the current game state:
```python
@dataclass
class State:
    qi: int
    stability: int
    completion: int
    perfection: int
    control_buff_turns: int      # Remaining turns of +40% control
    intensity_buff_turns: int    # Remaining turns of +40% intensity
    history: List[str]           # Actions taken
```

Key methods:
- `get_score(target_completion=0, target_perfection=0)` → With targets: sum of progress toward each (capped). Without targets: `min(completion, perfection)`
- `targets_met(target_completion, target_perfection)` → Returns `True` if both targets are reached
- `get_control(base)` → applies buff if active
- `get_intensity(base)` → applies buff if active

#### `CraftingOptimizer`
Main optimizer class containing:
- Base stats configuration
- Skill definitions dictionary
- Search algorithms
- State manipulation methods

### Skills Dictionary Structure
```python
self.skills = {
    "skill_key": (
        "Display Name",    # [0] Human-readable name
        qi_cost,           # [1] Qi consumed
        stability_cost,    # [2] Stability cost (positive = spend, negative = restore)
        completion_gain,   # [3] Base completion gained
        perfection_gain,   # [4] Base perfection gained
        BuffType,          # [5] NONE, CONTROL, or INTENSITY
        buff_duration      # [6] Turns the buff lasts
    ),
}
```

### Available Skills
**Sign convention (matches code)**:
- `stability_cost > 0` means you **spend** stability (usually `10`)
- `stability_cost < 0` means you **restore** stability (e.g. `-40`, `-15`)

| Skill | Qi Cost | Stability Cost | Completion | Perfection | Buff |
|-------|---------|-----------|------------|------------|------|
| Simple Fusion | 0 | 10 | 12 | 0 | None |
| Energised Fusion | 10 | 10 | 21 | 0 | None |
| Cycling Fusion | 10 | 10 | 9 | 0 | Control +40% (2 turns) |
| Disciplined Touch | 10 | 10 | 6* | 6* | None |
| Cycling Refine | 10 | 10 | 0 | 12* | Intensity +40% (2 turns) |
| Simple Refine | 18 | 10 | 0 | 16* | None |
| Forceful Stabilize | 88 | -40 | 0 | 0 | None |
| Instant Restoration | 44 | -15 | 0 | 0 | None |

*Scales with stats/buffs. `Disciplined Touch` scales with **Intensity only** (not `control_condition`). `Cycling Refine` and `Simple Refine` scale with **Control** and are affected by `control_condition`.

---

## Search Algorithms

### 1. Exhaustive Search with Pareto Pruning (`search_optimal`)
- **Method**: BFS with Pareto-frontier pruning
- **Pruning**: For each resource state (qi, stability, buffs), only keeps non-dominated (completion, perfection) pairs
- **Parameters**: `target_completion=0, target_perfection=0` — when provided, optimizes toward targets and stops early when met
- **Returns**: Globally optimal rotation (score 76 in legacy mode, or first rotation meeting targets)

### 2. Greedy Search (`greedy_search`)
- **Method**: Always picks best immediate action with balance penalty
- **Parameters**: `target_completion=0, target_perfection=0` — when provided, penalizes overshooting targets and stops early when met
- **Use Case**: Quick approximation (achieves score ~54 in legacy mode)

### 3. Forecast-Aware Lookahead (`suggest_next_turn`)
- **Method**: DFS with memoization over control forecast horizon
- **Input**: Current state + list of control multipliers for upcoming turns + optional targets
- **Parameters**: `target_completion=0, target_perfection=0` — when provided, optimizes toward targets and stops early when met
- **Returns**: Best first action, full plan, and horizon score/progress

**Important**: Only `suggest_next_turn` is condition-aware. `search_optimal()` and `greedy_search()` assume neutral control condition (`1.0`) every turn.

---

## CLI Usage

### Command Line Options

| Short | Long | Description |
|-------|------|-------------|
| `-i` | `--interactive` | Interactive mode (turn-by-turn) |
| `-t` | `--targets` | Set both targets at once: `-t 60 60` |
| `-c` | `--target-completion` | Target completion value |
| `-p` | `--target-perfection` | Target perfection value |
| `-s` | `--suggest-next` | Suggest best action for forecast |
| `-f` | `--forecast-control` | Control forecast (e.g. `1.5,1,0.5,1`) |
| | `--config` | Path to custom config file |

### Target-Based Optimal Search (Recommended)
```bash
python3 wuxia_crafting_optimizer.py -t 50 50
```
Finds the optimal rotation to reach the specified completion and perfection targets. Use `-t COMP PERF` as shorthand, or `-c COMP -p PERF` for separate flags.

### Legacy Optimal Search (Balanced Mode)
```bash
python3 wuxia_crafting_optimizer.py
```
Without targets, maximizes `min(completion, perfection)`. Outputs: Optimal rotation, detailed step-by-step breakdown, greedy comparison.

### Using a Configuration File
```bash
python3 wuxia_crafting_optimizer.py --config config.json -t 50 50
```
Load stats and skills from a JSON configuration file instead of using hardcoded defaults. See [Configuration File](#configuration-file) section for format details.

### Forecast-Aware Suggestion
```bash
# With targets
python3 wuxia_crafting_optimizer.py -s -f '1.5,1,0.5,1' -t 50 50

# Legacy mode (balanced scoring)
python3 wuxia_crafting_optimizer.py -s -f '1.5,1,0.5,1'
```
- When mirroring the game UI, provide exactly **4** values: `[t, t+1, t+2, t+3]` (current turn first).
- `1.5` = +50% control this turn
- `1.0` = normal control
- `0.5` = -50% control

### Interactive Mode
```bash
# With targets (recommended)
python3 wuxia_crafting_optimizer.py -i -t 60 60

# Legacy mode (balanced scoring)
python3 wuxia_crafting_optimizer.py -i
```
Step-by-step crafting session with turn-by-turn forecast input. Ideal for playing alongside the game in real-time.

**Turn Flow:**
1. Show turn status and current state (with target progress if targets set)
2. Ask for control forecast:
   - **Turn 1:** Enter all 4 values (current + next 3 turns)
   - **Turn 2+:** Previous forecast shifts automatically (T1→T0, T2→T1, T3→T2), then enter only the new T3 value
3. Show AI-suggested optimal action (calculated using your forecast)
4. Show available skills (with gains calculated using your forecast)
5. Ask for skill selection
6. Apply skill with the provided forecast
7. Session ends automatically when both targets are met (if targets provided)

**Features:**
- Enter control forecast first each turn (matches game UI where conditions are visible before skill selection)
- **Forecast shifting:** After turn 1, previous forecast values shift automatically and you only enter the new T3 value (or 4 values to override)
- AI suggestion calculated using your forecast for accurate recommendations
- Get AI-suggested optimal action with lookahead plan (displayed only when 2+ actions planned)
- Accept suggestion or choose a different skill (by number or partial name)
- Ambiguous skill name detection (prompts for clarification when multiple skills match)
- Visual progress bars for Qi, Stability, Completion, Perfection
- Target progress display showing remaining completion/perfection needed (when targets set)
- Automatic session completion when targets are met
- Undo support to revert mistakes (also restores previous forecast)

**Commands during interactive mode:**
| Command | Description |
|---------|-------------|
| `help` / `h` | Show detailed help |
| `status` / `s` | Show detailed status with progress bars and action history |
| `undo` / `u` | Undo last action and return to previous turn |
| `quit` / `q` | Exit interactive mode |
| `<number>` | Select skill by its number in the list |
| `<partial name>` | Select skill by partial name match (e.g., "energised") |

**Example session (Turn 1 - enter all 4 values):**
```
► Forecast (e.g. '1.5,1,0.5,1') [Enter=default]: 1.5,1,0.5,1
  Forecast: T0: +50% │ T1: normal │ T2: -50% │ T3: normal

  ┌──────────────────────────────────────────────────┐
  │ ★ SUGGESTED: Simple Refine                       │
  │   -18 Qi, -10 Stab, +24 Perf                     │
  └──────────────────────────────────────────────────┘

  Available skills:
    1. Simple Fusion       -10 Stab, +12 Comp
    2. Energised Fusion   -10 Qi, -10 Stab, +21 Comp
    ...
  ★ 6. Simple Refine      -18 Qi, -10 Stab, +24 Perf
    ...

► Select skill [Enter=accept suggestion]: 

  ╔══════════════════════════════════════════════════╗
  ║ ✓ APPLIED: Simple Refine                        ║
  ║   Qi -18 │ Stab -10 │ Perf +24                  ║
  ╚══════════════════════════════════════════════════╝
```

**Example session (Turn 2+ - forecast shifts, enter only new T3):**
```
  Previous forecast shifted: T0=1, T1=-50%, T2=1
► New T3 value (e.g. '1.5') [Enter=1, or 4 values to override]: 0.5
  Forecast: T0: normal │ T1: -50% │ T2: normal │ T3: -50%

  ┌──────────────────────────────────────────────────┐
  │ ★ SUGGESTED: Energised Fusion                    │
  │   -10 Qi, -10 Stab, +21 Comp                     │
  └──────────────────────────────────────────────────┘
```

**Ambiguous name handling:**
```
► Select skill [Enter=accept suggestion]: simple
  ✗ Ambiguous: 'simple' matches multiple skills:
      1. Simple Fusion
      6. Simple Refine
    Please enter the number to select.
```

---

## Configuration File

The optimizer supports loading stats and skills from a JSON configuration file via the `--config` CLI option. If no config file is provided, built-in defaults are used.

### Configuration File Format
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
    "skill_key": {
      "name": "Display Name",
      "qi_cost": 10,
      "stability_cost": 10,
      "completion_gain": 0,
      "perfection_gain": 12,
      "buff_type": "NONE",
      "buff_duration": 0
    }
  }
}
```

### Stats Section
| Field | Description |
|-------|-------------|
| `max_qi` | Maximum Qi pool |
| `max_stability` | Maximum Stability pool |
| `base_intensity` | Base Intensity stat (affects completion) |
| `base_control` | Base Control stat (affects perfection) |
| `min_stability` | Minimum stability threshold (must restore before dropping below) |

### Skills Section
Each skill is keyed by a unique identifier (e.g., `simple_fusion`) and contains:
| Field | Description |
|-------|-------------|
| `name` | Human-readable display name |
| `qi_cost` | Qi consumed when using the skill |
| `stability_cost` | Stability cost (positive = spend, negative = restore) |
| `completion_gain` | Base completion gained |
| `perfection_gain` | Base perfection gained |
| `buff_type` | One of: `"NONE"`, `"CONTROL"`, `"INTENSITY"` |
| `buff_duration` | Number of turns the buff lasts |

A default `config.json` file is provided in the project root and is loaded automatically when no `--config` path is provided.

---

## Common Modification Scenarios

### Adding a New Skill
**Option 1: Via Configuration File (Recommended)**
1. Add a new skill entry to the `skills` section in your `config.json`
2. If skill has special scaling logic, add handling in `apply_skill()`
3. Update the skills table in this document

**Option 2: Via Code**
1. Add entry to the default config in `load_config()` function
2. If skill has special scaling logic, add handling in `apply_skill()`
3. Update the skills table in this document

### Changing Player Stats
**Option 1: Via Configuration File (Recommended)**
Modify the `stats` section in your `config.json`:
```json
{
  "stats": {
    "max_qi": 194,
    "max_stability": 60,
    "base_intensity": 12,
    "base_control": 16,
    "min_stability": 10
  }
}
```

**Option 2: Via Code**
Modify the default values in the `load_config()` function.

### Adding New Buff Types
1. Add to `BuffType` enum
2. Add tracking field to `State` dataclass
3. Add buff application logic in `State.get_*()` methods
4. Handle buff duration in `apply_skill()`

### Modifying Scoring Logic
Change `State.get_score()` method. Current behavior:
- With targets: `min(completion, target_completion) + min(perfection, target_perfection)`
- Without targets (legacy): `min(completion, perfection)`

The `targets_met()` method checks if both `completion >= target_completion` and `perfection >= target_perfection`.

---

## Critical Implementation Details

### Buff Application Order (in `apply_skill`)
1. Check resource requirements (qi, stability)
2. Calculate gains using EXISTING buffs (not new ones from this action)
3. Apply costs
4. Apply gains
5. Decrement existing buff durations
6. Apply NEW buffs from this skill

### Stability Validation
```python
# CRITICAL: This check must remain
if stability_cost > 0 and new_state.stability - stability_cost < self.min_stability:
    return None
```

### Control Condition Application
Only affects Control-scaling skills (Simple Refine, Cycling Refine):
```python
control = int(state.get_control(self.base_control) * control_condition)
```
Does NOT affect Disciplined Touch (scales with Intensity only).

---

## Testing Recommendations

### Verify Optimal Score (Legacy Mode)
```python
optimizer = CraftingOptimizer()
state = optimizer.search_optimal()
assert state.get_score() == 76
assert state.completion == 80
assert state.perfection == 76
```

### Verify Target-Based Search
```python
optimizer = CraftingOptimizer()
state = optimizer.search_optimal(target_completion=50, target_perfection=50)
assert state.targets_met(50, 50)
assert state.completion >= 50
assert state.perfection >= 50
# Score with targets = min(completion, 50) + min(perfection, 50) = 100
assert state.get_score(50, 50) == 100
```

### Test Buff Timing
Ensure buffs from cycling skills don't apply to the same turn:
```python
state = State(qi=194, stability=60, completion=0, perfection=0,
              control_buff_turns=0, intensity_buff_turns=0, history=[])
# Cycling Refine should give base 12 perfection, not buffed
new_state = optimizer.apply_skill(state, "cycling_refine")
assert new_state.perfection == 12  # Not 16 (buffed)
assert new_state.intensity_buff_turns == 2  # Buff now active for next turns
```

### Test Control Conditions
```python
# Simple Refine with +50% control
state = State(qi=194, stability=60, completion=0, perfection=0,
              control_buff_turns=0, intensity_buff_turns=0, history=[])
new_state = optimizer.apply_skill(state, "simple_refine", control_condition=1.5)
assert new_state.perfection == 24  # 16 * 1.5 = 24
```

---

## Known Optimal Rotations

### Legacy Mode (Score: 76)
Without targets, maximizes `min(completion, perfection)`:

```
1. Energised Fusion      (+21 Completion)
2. Energised Fusion      (+21 Completion)
3. Energised Fusion      (+21 Completion)
4. Cycling Refine        (+12 Perfection, grants Intensity buff)
5. Disciplined Touch     (+8 Completion, +8 Perfection) [with Intensity buff]
6. Forceful Stabilize    (+40 Stability)
7. Cycling Fusion        (+9 Completion, grants Control buff)
8. Simple Refine         (+22 Perfection) [with Control buff]
9. Simple Refine         (+22 Perfection) [with Control buff]
10. Cycling Refine       (+12 Perfection)
```

**Final**: Completion=80, Perfection=76, Score=76

### Target Mode Example (Targets: 50/50)
With `-t 50 50`, finds an optimal rotation to reach targets under the capped target-mode score (it may stop early as soon as both targets are met):

```
1. Energised Fusion      (+21 Completion)
2. Energised Fusion      (+21 Completion)
3. Cycling Refine        (+12 Perfection, grants Intensity buff)
4. Disciplined Touch     (+8 Completion, +8 Perfection) [with Intensity buff]
5. Simple Refine         (+16 Perfection)
6. Simple Refine         (+16 Perfection)
7. Cycling Refine        (+12 Perfection)
```

**Final**: Completion=50, Perfection=64, Targets Met ✓

---

## Troubleshooting

### "No valid action found"
- Check if stability would drop below 10
- Check if qi is sufficient for the action

### Score lower than 76 (legacy mode)
- Verify `min_stability = 10` constraint is enforced
- Verify buff timing (buffs apply to subsequent turns)
- Check that Pareto pruning isn't too aggressive

### Targets not being met
- Ensure targets are provided together (use `-t 50 50` or `-c 50 -p 50`)
- Check if targets are achievable with current stats and resources
- Verify the optimizer isn't stopping early due to resource constraints

### Forecast suggestions seem wrong
- Verify control_condition only affects Control-scaling skills
- Check that forecast list is in correct order (current turn first)

### "Error: targets must be provided together"
- Both target arguments are required when using target mode
- Use `-t COMP PERF` shorthand, or `-c COMP -p PERF` for separate flags
- Either provide both or neither (for legacy balanced mode)

---

## Glossary / Mapping to Game Terms
- Game “random Qi control condition” → `control_condition` per-turn multiplier
- “Cycling Fusion buff” → `control_buff_turns` (`+40%` control)
- “Cycling Refine buff” → `intensity_buff_turns` (`+40%` intensity)

---

## Common Agent Pitfalls (Read This Before Editing)
- Don’t apply new cycling buffs on the same turn they are cast (they apply next turn).
- Preserve buff duration update order (decrement existing buffs, then apply new buff).
- Preserve the stability sign convention (`>0` spend, `<0` restore) and the `>= 10` post-action invariant.
- Don’t “improve” integer flooring into rounding without updating expected outcomes.

---

## File Structure

```
Project Root
├── config.json                 # Default configuration file (stats and skills)
├── wuxia_crafting_optimizer.py
│   ├── BuffType (Enum)
│   ├── State (dataclass)
│   ├── load_config             # Load and validate JSON configuration
│   ├── CraftingOptimizer
│   │   ├── __init__              # Initialize from config (file or defaults)
│   │   ├── apply_skill           # Core skill application logic
│   │   ├── is_terminal           # Check if game over
│   │   ├── search_optimal        # Exhaustive Pareto search
│   │   ├── greedy_search         # Quick approximation
│   │   ├── simulate_rotation     # Test specific rotation
│   │   ├── get_skill_key_from_name  # Lookup skill key by display name
│   │   └── print_* methods       # Output formatting
│   ├── Helper Functions
│   │   ├── _parse_control_forecast  # Parse forecast string to list of floats
│   │   ├── _make_bar             # Create text-based progress bar
│   │   └── _format_skill_details # Format skill costs/gains for display
│   ├── suggest_next_turn         # DFS lookahead with control forecast
│   ├── interactive_mode          # Turn-by-turn interactive crafting session
│   └── main
└── AGENTS.md                   # This documentation file
```
