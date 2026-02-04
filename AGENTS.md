# AGENTS.md - Wuxia Crafting Optimizer

This document provides guidance for AI agents and developers working with the Wuxia Crafting Optimizer codebase.

---

## Project Overview

**Purpose**: This script finds the optimal skill rotation for a wuxia game crafting system. The goal is to maximize both completion and perfection bars before running out of stability.

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
2. **Scoring**: Final score = `min(completion, perfection)` — both bars must be balanced.
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
- `get_score()` → `min(completion, perfection)`
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

*Scales with stats/buffs

---

## Search Algorithms

### 1. Exhaustive Search with Pareto Pruning (`search_optimal`)
- **Method**: BFS with Pareto-frontier pruning
- **Pruning**: For each resource state (qi, stability, buffs), only keeps non-dominated (completion, perfection) pairs
- **Returns**: Globally optimal rotation achieving score 76

### 2. Greedy Search (`greedy_search`)
- **Method**: Always picks best immediate action with balance penalty
- **Use Case**: Quick approximation (achieves score ~54)

### 3. Forecast-Aware Lookahead (`suggest_next_turn`)
- **Method**: DFS with memoization over control forecast horizon
- **Input**: Current state + list of control multipliers for upcoming turns
- **Returns**: Best first action, full plan, and horizon score

**Important**: Only `suggest_next_turn` is condition-aware. `search_optimal()` and `greedy_search()` assume neutral control condition (`1.0`) every turn.

---

## CLI Usage

### Basic Optimal Search
```bash
python3 wuxia_crafting_optimizer.py
```
Outputs: Optimal rotation, detailed step-by-step breakdown, greedy comparison.

### Forecast-Aware Suggestion
```bash
python3 wuxia_crafting_optimizer.py --suggest-next --forecast-control '1.5,1,0.5,1'
```
- When mirroring the game UI, provide exactly **4** values: `[t, t+1, t+2, t+3]` (current turn first).
- `1.5` = +50% control this turn
- `1.0` = normal control
- `0.5` = -50% control

### Interactive Mode
```bash
python3 wuxia_crafting_optimizer.py --interactive
```
Step-by-step crafting session with turn-by-turn forecast input. Ideal for playing alongside the game in real-time.

**Features:**
- Enter control forecasts each turn (4 values for current + next 3 turns)
- Get AI-suggested optimal action with lookahead plan (displayed only when 2+ actions planned)
- Accept suggestion or choose a different skill (by number or partial name)
- Ambiguous skill name detection (prompts for clarification when multiple skills match)
- Visual progress bars for Qi, Stability, Completion, Perfection
- Undo support to revert mistakes

**Commands during interactive mode:**
| Command | Description |
|---------|-------------|
| `help` / `h` | Show detailed help |
| `status` / `s` | Show detailed status with progress bars and action history |
| `undo` / `u` | Undo last action and return to previous turn |
| `quit` / `q` | Exit interactive mode |
| `<number>` | Select skill by its number in the list |
| `<partial name>` | Select skill by partial name match (e.g., "energised") |

**Example session:**
```
► Forecast (e.g. '1.5,1,0.5,1') [Enter=default]: 1.5,1,0.5,1
  Forecast: T0: +50% │ T1: normal │ T2: -50% │ T3: normal

  ┌──────────────────────────────────────────────────┐
  │ ★ SUGGESTED: Energised Fusion                    │
  │   -10 Qi, -10 Stab, +21 Comp                     │
  └──────────────────────────────────────────────────┘

► Select skill [Enter=accept suggestion]: 
  ┌──────────────────────────────────────────────────┐
  │ ✓ Applied: Energised Fusion                      │
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

## Common Modification Scenarios

### Adding a New Skill
1. Add entry to `self.skills` dictionary in `__init__`
2. If skill has special scaling logic, add handling in `apply_skill()`
3. Update the skills table in this document

### Changing Player Stats
Modify these values in `CraftingOptimizer.__init__()`:
```python
self.max_qi = 194
self.max_stability = 60
self.base_intensity = 12
self.base_control = 16
self.min_stability = 10
```

### Adding New Buff Types
1. Add to `BuffType` enum
2. Add tracking field to `State` dataclass
3. Add buff application logic in `State.get_*()` methods
4. Handle buff duration in `apply_skill()`

### Modifying Scoring Logic
Change `State.get_score()` method. Current: `min(completion, perfection)`

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

### Verify Optimal Score
```python
optimizer = CraftingOptimizer()
state = optimizer.search_optimal()
assert state.get_score() == 76
assert state.completion == 80
assert state.perfection == 76
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

## Known Optimal Rotation (Score: 76)

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

---

## Troubleshooting

### "No valid action found"
- Check if stability would drop below 10
- Check if qi is sufficient for the action

### Score lower than 76
- Verify `min_stability = 10` constraint is enforced
- Verify buff timing (buffs apply to subsequent turns)
- Check that Pareto pruning isn't too aggressive

### Forecast suggestions seem wrong
- Verify control_condition only affects Control-scaling skills
- Check that forecast list is in correct order (current turn first)

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
wuxia_crafting_optimizer.py
├── BuffType (Enum)
├── State (dataclass)
├── CraftingOptimizer
│   ├── __init__              # Stats and skills config
│   ├── apply_skill           # Core skill application logic
│   ├── is_terminal           # Check if game over
│   ├── search_optimal        # Exhaustive Pareto search
│   ├── greedy_search         # Quick approximation
│   ├── simulate_rotation     # Test specific rotation
│   ├── get_skill_key_from_name  # Lookup skill key by display name
│   └── print_* methods       # Output formatting
├── Helper Functions
│   ├── _parse_control_forecast  # Parse forecast string to list of floats
│   ├── _make_bar             # Create text-based progress bar
│   └── _format_skill_details # Format skill costs/gains for display
├── suggest_next_turn         # DFS lookahead with control forecast
├── interactive_mode          # Turn-by-turn interactive crafting session
└── main
```
