#!/usr/bin/env python3
"""
Ascend From Nine Mountains - Crafting Optimizer
Finds the optimal skill rotation to reach target completion and perfection
before running out of stability.

Rules:
- Most actions cost stability; see the skill list/config for exact costs
- Stability MUST be restored BEFORE going below 10
- Goal: Reach target completion and perfection values
"""

from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional, Any
from enum import Enum
from collections import deque
import argparse
import json
import os


class BuffType(Enum):
    NONE = 0
    CONTROL = 1  # 40% buff to control
    INTENSITY = 2  # 40% buff to intensity


@dataclass
class State:
    qi: int
    stability: int
    max_stability: int  # Current max stability (decreases by 1 each turn)
    completion: int
    perfection: int
    control_buff_turns: int  # Remaining turns of control buff
    intensity_buff_turns: int  # Remaining turns of intensity buff
    history: List[str]

    def copy(self):
        return State(
            qi=self.qi,
            stability=self.stability,
            max_stability=self.max_stability,
            completion=self.completion,
            perfection=self.perfection,
            control_buff_turns=self.control_buff_turns,
            intensity_buff_turns=self.intensity_buff_turns,
            history=self.history.copy(),
        )

    def get_control(self, base_control: int) -> int:
        if self.control_buff_turns > 0:
            return int(base_control * 1.4)
        return base_control

    def get_intensity(self, base_intensity: int) -> int:
        if self.intensity_buff_turns > 0:
            return int(base_intensity * 1.4)
        return base_intensity

    def get_score(self, target_completion: int = 0, target_perfection: int = 0) -> int:
        """Score based on progress toward targets.

        If targets are 0, falls back to min(completion, perfection) for backward compatibility.
        Otherwise, returns sum of min(actual, target) for both metrics.
        """
        if target_completion == 0 and target_perfection == 0:
            return min(self.completion, self.perfection)
        comp_progress = min(self.completion, target_completion)
        perf_progress = min(self.perfection, target_perfection)
        return comp_progress + perf_progress

    def targets_met(self, target_completion: int, target_perfection: int) -> bool:
        """Check if both targets have been reached."""
        return (
            self.completion >= target_completion
            and self.perfection >= target_perfection
        )

    def get_total(self) -> int:
        """Total of completion and perfection"""
        return self.completion + self.perfection

    def __str__(self):
        return (
            f"Qi: {self.qi}, Stability: {self.stability}, "
            f"Completion: {self.completion}, Perfection: {self.perfection}"
        )


def load_config(config_path: Optional[str] = None) -> Dict[str, Any]:
    """Load configuration from a JSON file.

    If config_path is None, loads `config.json` from next to this script when present,
    otherwise returns the embedded default configuration.
    """
    if config_path is None:
        default_path = os.path.join(os.path.dirname(__file__), "config.json")
        if os.path.exists(default_path):
            config_path = default_path
        else:
            # Return embedded default configuration
            return {
                "stats": {
                    "max_qi": 194,
                    "max_stability": 60,
                    "base_intensity": 12,
                    "base_control": 16,
                    "min_stability": 10,
                },
                "skills": {
                    "simple_fusion": {
                        "name": "Simple Fusion",
                        "qi_cost": 0,
                        "stability_cost": 10,
                        "completion_gain": 12,
                        "perfection_gain": 0,
                        "buff_type": "NONE",
                        "buff_duration": 0,
                    },
                    "energised_fusion": {
                        "name": "Energised Fusion",
                        "qi_cost": 10,
                        "stability_cost": 10,
                        "completion_gain": 21,
                        "perfection_gain": 0,
                        "buff_type": "NONE",
                        "buff_duration": 0,
                    },
                    "cycling_fusion": {
                        "name": "Cycling Fusion",
                        "qi_cost": 10,
                        "stability_cost": 10,
                        "completion_gain": 9,
                        "perfection_gain": 0,
                        "buff_type": "CONTROL",
                        "buff_duration": 2,
                    },
                    "disciplined_touch": {
                        "name": "Disciplined Touch",
                        "qi_cost": 10,
                        "stability_cost": 10,
                        "completion_gain": 0,
                        "perfection_gain": 0,
                        "buff_type": "NONE",
                        "buff_duration": 0,
                    },
                    "cycling_refine": {
                        "name": "Cycling Refine",
                        "qi_cost": 10,
                        "stability_cost": 10,
                        "completion_gain": 0,
                        "perfection_gain": 12,
                        "buff_type": "INTENSITY",
                        "buff_duration": 2,
                    },
                    "simple_refine": {
                        "name": "Simple Refine",
                        "qi_cost": 18,
                        "stability_cost": 10,
                        "completion_gain": 0,
                        "perfection_gain": 16,
                        "buff_type": "NONE",
                        "buff_duration": 0,
                    },
                    "forceful_stabilize": {
                        "name": "Forceful Stabilize",
                        "qi_cost": 88,
                        "stability_cost": -40,
                        "completion_gain": 0,
                        "perfection_gain": 0,
                        "buff_type": "NONE",
                        "buff_duration": 0,
                    },
                    "instant_restoration": {
                        "name": "Instant Restoration",
                        "qi_cost": 44,
                        "stability_cost": -15,
                        "completion_gain": 0,
                        "perfection_gain": 0,
                        "buff_type": "NONE",
                        "buff_duration": 0,
                    },
                },
            }

    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    with open(config_path, "r") as f:
        config = json.load(f)

    # Validate required sections
    if "stats" not in config:
        raise ValueError("Configuration file must contain 'stats' section")
    if "skills" not in config:
        raise ValueError("Configuration file must contain 'skills' section")

    # Validate required stats
    required_stats = [
        "max_qi",
        "max_stability",
        "base_intensity",
        "base_control",
        "min_stability",
    ]
    for stat in required_stats:
        if stat not in config["stats"]:
            raise ValueError(f"Configuration 'stats' section must contain '{stat}'")

    # Validate skills structure
    required_skill_fields = [
        "name",
        "qi_cost",
        "stability_cost",
        "completion_gain",
        "perfection_gain",
        "buff_type",
        "buff_duration",
        "prevents_max_stability_decay",
    ]
    for skill_key, skill_data in config["skills"].items():
        for field in required_skill_fields:
            if field not in skill_data:
                raise ValueError(f"Skill '{skill_key}' must contain '{field}'")
        # Validate buff_type
        if skill_data["buff_type"] not in ["NONE", "CONTROL", "INTENSITY"]:
            raise ValueError(
                f"Skill '{skill_key}' has invalid buff_type: {skill_data['buff_type']}"
            )

    return config


class CraftingOptimizer:
    def __init__(self, config_path: Optional[str] = None):
        # Load configuration
        config = load_config(config_path)

        # Base stats from config
        stats = config["stats"]
        self.max_qi = stats["max_qi"]
        self.max_stability = stats["max_stability"]
        self.base_intensity = stats["base_intensity"]
        self.base_control = stats["base_control"]
        self.min_stability = stats[
            "min_stability"
        ]  # Must restore BEFORE going below this

        # Convert skills from config format to internal tuple format
        # Internal format: (name, qi_cost, stability_cost, completion_gain, perfection_gain, buff_type, buff_duration, prevents_max_stability_decay)
        buff_type_map = {
            "NONE": BuffType.NONE,
            "CONTROL": BuffType.CONTROL,
            "INTENSITY": BuffType.INTENSITY,
        }

        self.skills = {}
        for skill_key, skill_data in config["skills"].items():
            self.skills[skill_key] = (
                skill_data["name"],
                skill_data["qi_cost"],
                skill_data["stability_cost"],
                skill_data["completion_gain"],
                skill_data["perfection_gain"],
                buff_type_map[skill_data["buff_type"]],
                skill_data["buff_duration"],
                skill_data.get("prevents_max_stability_decay", False),
            )

    def calculate_disciplined_touch(self, state: State) -> Tuple[int, int]:
        """Disciplined Touch: 6 Completion and 6 Perfection, both scaling with intensity"""
        intensity = state.get_intensity(self.base_intensity)
        # Both scale with intensity
        completion = 6 * intensity // 12  # Base is 6 at 12 intensity
        perfection = 6 * intensity // 12
        return completion, perfection

    def calculate_skill_gains(
        self, state: State, skill_key: str, control_condition: float = 1.0
    ) -> Tuple[int, int]:
        """Return (completion_gain, perfection_gain) for `skill_key` using the CURRENT state's buffs.

        Important: this must not apply any NEW buffs granted by the skill itself (those only affect
        subsequent turns).
        """

        _, _, _, base_comp, base_perf, _, _, _ = self.skills[skill_key]
        completion_gain = base_comp
        perfection_gain = base_perf

        if skill_key == "disciplined_touch":
            completion_gain, perfection_gain = self.calculate_disciplined_touch(state)
        elif skill_key in ["cycling_refine", "simple_refine"]:
            # These scale with control (from EXISTING buffs, not new ones)
            # plus a per-turn external control condition (e.g. +/- 50%).
            control = int(state.get_control(self.base_control) * control_condition)
            if skill_key == "cycling_refine":
                perfection_gain = 12 * control // 16  # Base is 12 at 16 control
            else:  # simple_refine
                perfection_gain = 16 * control // 16
            completion_gain = 0

        return completion_gain, perfection_gain

    def apply_skill(
        self, state: State, skill_key: str, control_condition: float = 1.0
    ) -> Optional[State]:
        """Apply a skill and return new state, or None if invalid.

        `control_condition` is a per-turn multiplier applied to Control-based skills
        (e.g. random condition that changes Qi control by +/- 50%).
        """
        skill = self.skills[skill_key]
        (
            name,
            qi_cost,
            stability_cost,
            completion_gain,
            perfection_gain,
            buff_type,
            buff_duration,
            prevents_max_stability_decay,
        ) = skill

        new_state = state.copy()

        # Check resources
        if new_state.qi < qi_cost:
            return None

        # CRITICAL: Stability must stay >= min_stability (10)
        # If this skill costs stability and would drop us below min_stability, reject it
        if (
            stability_cost > 0
            and new_state.stability - stability_cost < self.min_stability
        ):
            return None

        # Calculate gains BEFORE applying buffs from this skill
        # (buffs from cycling skills apply to NEXT turns, not this turn)
        completion_gain, perfection_gain = self.calculate_skill_gains(
            state, skill_key, control_condition=control_condition
        )

        # Apply costs
        new_state.qi -= qi_cost
        new_state.stability -= stability_cost

        # Cap stability at current max
        if new_state.stability > new_state.max_stability:
            new_state.stability = new_state.max_stability

        # Apply gains
        new_state.completion += completion_gain
        new_state.perfection += perfection_gain

        # Decrement existing buff durations first
        if new_state.control_buff_turns > 0:
            new_state.control_buff_turns -= 1
        if new_state.intensity_buff_turns > 0:
            new_state.intensity_buff_turns -= 1

        # Apply NEW buffs from this skill (they will be active next turn)
        if buff_type == BuffType.CONTROL:
            new_state.control_buff_turns = buff_duration
        elif buff_type == BuffType.INTENSITY:
            new_state.intensity_buff_turns = buff_duration

        # Decrease max stability by 1 each turn, unless this skill prevents it
        if not prevents_max_stability_decay:
            new_state.max_stability = max(0, new_state.max_stability - 1)
            # Also cap current stability to new max
            if new_state.stability > new_state.max_stability:
                new_state.stability = new_state.max_stability

        new_state.history.append(name)
        return new_state

    def is_terminal(self, state: State) -> bool:
        """Check if we've reached a terminal state (no valid actions possible)"""
        # Check if any action is possible
        for skill_key in self.skills:
            skill = self.skills[skill_key]
            _, qi_cost, stability_cost, _, _, _, _, prevents_max_stability_decay = skill
            # Check qi requirement
            if state.qi < qi_cost:
                continue
            # Check stability requirement - must stay >= min_stability after action
            if (
                stability_cost > 0
                and state.stability - stability_cost < self.min_stability
            ):
                continue
            # This action is valid
            return False
        return True

    @dataclass(frozen=True)
    class _Resources:
        qi: int
        stability: int
        max_stability: int
        control_buff_turns: int
        intensity_buff_turns: int

    @dataclass
    class _Node:
        completion: int
        perfection: int
        prev_res: Optional["CraftingOptimizer._Resources"]
        prev_node_idx: Optional[int]
        action_name: Optional[str]

        def score(self, target_completion: int = 0, target_perfection: int = 0) -> int:
            if target_completion == 0 and target_perfection == 0:
                return min(self.completion, self.perfection)
            comp_progress = min(self.completion, target_completion)
            perf_progress = min(self.perfection, target_perfection)
            return comp_progress + perf_progress

    def _dominates(
        self, a: "CraftingOptimizer._Node", b: "CraftingOptimizer._Node"
    ) -> bool:
        return a.completion >= b.completion and a.perfection >= b.perfection

    def _insert_pareto(
        self,
        frontier: Dict["CraftingOptimizer._Resources", List["CraftingOptimizer._Node"]],
        res: "CraftingOptimizer._Resources",
        node: "CraftingOptimizer._Node",
    ) -> Optional[int]:
        """Insert node into pareto frontier for a given resource state.

        Returns the index of the inserted node within frontier[res] if kept,
        otherwise None if dominated.
        """
        lst = frontier.setdefault(res, [])

        # If dominated by existing, discard
        for existing in lst:
            if self._dominates(existing, node):
                return None

        # IMPORTANT: Don't physically remove dominated nodes here.
        # We keep indices stable because the search queue stores (res, idx).
        lst.append(node)
        return len(lst) - 1

    def _reconstruct_history(
        self,
        frontier: Dict["CraftingOptimizer._Resources", List["CraftingOptimizer._Node"]],
        end_res: "CraftingOptimizer._Resources",
        end_idx: int,
    ) -> List[str]:
        actions: List[str] = []
        res = end_res
        idx = end_idx
        while True:
            node = frontier[res][idx]
            if node.action_name is None:
                break
            actions.append(node.action_name)
            if node.prev_res is None or node.prev_node_idx is None:
                break
            res = node.prev_res
            idx = node.prev_node_idx
        actions.reverse()
        return actions

    def search_optimal(
        self, target_completion: int = 0, target_perfection: int = 0
    ) -> State:
        """Exhaustive search with Pareto-pruning over resource states.

        Unlike the original depth-limited BFS, this explores until no further
        actions are possible, while pruning dominated (completion, perfection)
        pairs for the same (qi, stability, buffs).

        If target_completion and target_perfection are provided (non-zero),
        the search optimizes toward reaching those targets.
        """
        start_res = self._Resources(
            qi=self.max_qi,
            stability=self.max_stability,
            max_stability=self.max_stability,
            control_buff_turns=0,
            intensity_buff_turns=0,
        )
        frontier: Dict[CraftingOptimizer._Resources, List[CraftingOptimizer._Node]] = {}
        start_node = self._Node(
            completion=0,
            perfection=0,
            prev_res=None,
            prev_node_idx=None,
            action_name=None,
        )
        self._insert_pareto(frontier, start_res, start_node)

        q = deque([(start_res, 0)])
        best_res = start_res
        best_idx = 0

        target_score_cap = 0
        target_mode = target_completion > 0 and target_perfection > 0
        if target_mode:
            target_score_cap = target_completion + target_perfection

        while q:
            res, idx = q.popleft()
            node = frontier[res][idx]
            node_score = node.score(target_completion, target_perfection)
            if node_score > frontier[best_res][best_idx].score(
                target_completion, target_perfection
            ):
                best_res, best_idx = res, idx

            # In target mode, the score is capped at (target_completion + target_perfection).
            # As soon as we reach that cap, we have an optimal solution and can stop.
            if target_mode and node_score >= target_score_cap:
                best_res, best_idx = res, idx
                break

            state = State(
                qi=res.qi,
                stability=res.stability,
                max_stability=res.max_stability,
                completion=node.completion,
                perfection=node.perfection,
                control_buff_turns=res.control_buff_turns,
                intensity_buff_turns=res.intensity_buff_turns,
                history=[],
            )

            # Expand all valid actions
            for skill_key in self.skills:
                new_state = self.apply_skill(state, skill_key)
                if new_state is None:
                    continue

                new_res = self._Resources(
                    qi=new_state.qi,
                    stability=new_state.stability,
                    max_stability=new_state.max_stability,
                    control_buff_turns=new_state.control_buff_turns,
                    intensity_buff_turns=new_state.intensity_buff_turns,
                )
                new_node = self._Node(
                    completion=new_state.completion,
                    perfection=new_state.perfection,
                    prev_res=res,
                    prev_node_idx=idx,
                    action_name=self.skills[skill_key][0],
                )
                inserted_idx = self._insert_pareto(frontier, new_res, new_node)
                if inserted_idx is not None:
                    q.append((new_res, inserted_idx))

        history = self._reconstruct_history(frontier, best_res, best_idx)
        best_node = frontier[best_res][best_idx]
        return State(
            qi=best_res.qi,
            stability=best_res.stability,
            max_stability=best_res.max_stability,
            completion=best_node.completion,
            perfection=best_node.perfection,
            control_buff_turns=best_res.control_buff_turns,
            intensity_buff_turns=best_res.intensity_buff_turns,
            history=history,
        )

    def greedy_search(
        self, target_completion: int = 0, target_perfection: int = 0
    ) -> State:
        """Greedy approach: always pick the best immediate action.

        If targets are provided, prioritizes actions that move toward those targets.
        """
        state = State(
            qi=self.max_qi,
            stability=self.max_stability,
            max_stability=self.max_stability,
            completion=0,
            perfection=0,
            control_buff_turns=0,
            intensity_buff_turns=0,
            history=[],
        )

        while not self.is_terminal(state):
            # Stop early if targets are met
            if target_completion > 0 and target_perfection > 0:
                if state.targets_met(target_completion, target_perfection):
                    break

            best_next = None
            best_score = -1

            for skill_key in self.skills:
                new_state = self.apply_skill(state, skill_key)
                if new_state is not None:
                    if target_completion > 0 or target_perfection > 0:
                        # Score based on progress toward targets
                        score = new_state.get_score(
                            target_completion, target_perfection
                        )
                        # Penalize going over targets (wasted resources)
                        comp_over = max(0, new_state.completion - target_completion)
                        perf_over = max(0, new_state.perfection - target_perfection)
                        score -= (comp_over + perf_over) * 0.5
                    else:
                        # Legacy behavior: balance completion and perfection
                        score = new_state.get_score()
                        diff = abs(new_state.completion - new_state.perfection)
                        score -= diff * 0.5  # Penalize imbalance

                    if score > best_score:
                        best_score = score
                        best_next = new_state

            if best_next is None:
                break
            state = best_next

        return state

    def simulate_rotation(self, rotation: List[str]) -> State:
        """Simulate a specific rotation"""
        state = State(
            qi=self.max_qi,
            stability=self.max_stability,
            max_stability=self.max_stability,
            completion=0,
            perfection=0,
            control_buff_turns=0,
            intensity_buff_turns=0,
            history=[],
        )

        for skill_key in rotation:
            new_state = self.apply_skill(state, skill_key)
            if new_state is None:
                break
            state = new_state

        return state

    def print_state(
        self, state: State, target_completion: int = 0, target_perfection: int = 0
    ):
        """Pretty print a state"""
        print(f"  Qi: {state.qi}/{self.max_qi}")
        print(f"  Stability: {state.stability}/{self.max_stability}")
        if target_completion > 0:
            print(f"  Completion: {state.completion}/{target_completion}")
        else:
            print(f"  Completion: {state.completion}")
        if target_perfection > 0:
            print(f"  Perfection: {state.perfection}/{target_perfection}")
        else:
            print(f"  Perfection: {state.perfection}")
        if target_completion > 0 and target_perfection > 0:
            if state.targets_met(target_completion, target_perfection):
                print(f"  Status: ✓ TARGETS MET")
            else:
                comp_remaining = max(0, target_completion - state.completion)
                perf_remaining = max(0, target_perfection - state.perfection)
                print(
                    f"  Remaining: Completion={comp_remaining}, Perfection={perf_remaining}"
                )
        else:
            print(f"  Score (min): {state.get_score()}")
            print(f"  Balance: {abs(state.completion - state.perfection)}")
        print(f"  History ({len(state.history)} actions):")
        for i, action in enumerate(state.history, 1):
            print(f"    {i}. {action}")

    def print_detailed_rotation(
        self,
        rotation_keys: List[str],
        target_completion: int = 0,
        target_perfection: int = 0,
        control_conditions: Optional[List[float]] = None,
    ):
        """Print detailed step-by-step breakdown of a rotation.

        If `control_conditions` is provided, it is used as per-turn control multipliers
        for each step (extra steps default to 1.0).
        """
        state = State(
            qi=self.max_qi,
            stability=self.max_stability,
            max_stability=self.max_stability,
            completion=0,
            perfection=0,
            control_buff_turns=0,
            intensity_buff_turns=0,
            history=[],
        )

        print("\n  Step-by-step breakdown:")
        print(f"  {'=' * 70}")
        print(
            f"  Start: Qi={state.qi}, Stability={state.stability}, Completion=0, Perfection=0"
        )
        print(f"  {'=' * 70}")

        for i, skill_key in enumerate(rotation_keys, 1):
            old_qi = state.qi
            old_stab = state.stability
            old_comp = state.completion
            old_perf = state.perfection
            ctrl_buff = state.control_buff_turns > 0
            int_buff = state.intensity_buff_turns > 0

            cond = 1.0
            if control_conditions is not None:
                if 0 <= (i - 1) < len(control_conditions):
                    cond = control_conditions[i - 1]

            new_state = self.apply_skill(state, skill_key, control_condition=cond)
            if new_state is None:
                skill_name = self.skills[skill_key][0]
                print(f"  {i}. {skill_name} - FAILED (insufficient resources)")
                break

            qi_change = new_state.qi - old_qi
            stab_change = new_state.stability - old_stab
            comp_change = new_state.completion - old_comp
            perf_change = new_state.perfection - old_perf

            skill_name = self.skills[skill_key][0]
            buffs_str = []
            if ctrl_buff:
                buffs_str.append("Control+40%")
            if int_buff:
                buffs_str.append("Intensity+40%")
            buff_display = f" [{', '.join(buffs_str)}]" if buffs_str else ""

            cond_str = ""
            if control_conditions is not None:
                cond_str = f" (ControlCond x{cond:g})"

            print(f"  {i}. {skill_name}{buff_display}{cond_str}")
            print(f"     Qi: {old_qi} -> {new_state.qi} ({qi_change:+d})")
            print(
                f"     Stability: {old_stab} -> {new_state.stability} ({stab_change:+d})"
            )
            if comp_change > 0:
                print(
                    f"     Completion: {old_comp} -> {new_state.completion} ({comp_change:+d})"
                )
            if perf_change > 0:
                print(
                    f"     Perfection: {old_perf} -> {new_state.perfection} ({perf_change:+d})"
                )

            state = new_state

        print(f"  {'=' * 70}")
        if target_completion > 0 or target_perfection > 0:
            score = state.get_score(target_completion, target_perfection)
        else:
            score = state.get_score()
        print(
            f"  Final: Completion={state.completion}, Perfection={state.perfection}, Score={score}"
        )

    def get_skill_key_from_name(self, name: str) -> str:
        """Get skill key from display name"""
        for key, skill in self.skills.items():
            if skill[0] == name:
                return key
        raise ValueError(f"Unknown skill display name: {name}")


def _parse_control_forecast(s: str) -> List[float]:
    parts = [p.strip() for p in s.split(",") if p.strip()]
    if not parts:
        return []
    out: List[float] = []
    for p in parts:
        try:
            out.append(float(p))
        except ValueError as e:
            raise argparse.ArgumentTypeError(f"Invalid control multiplier: {p}") from e
    return out


def suggest_next_turn(
    optimizer: CraftingOptimizer,
    state: State,
    control_forecast: List[float],
    target_completion: int = 0,
    target_perfection: int = 0,
) -> Tuple[Optional[str], List[str], int]:
    """Return (best_first_skill_key, best_plan_keys, best_score_at_horizon).

    Uses a deterministic lookahead over the provided `control_forecast` multipliers.
    If targets are provided, optimizes toward reaching those targets.
    """

    if not control_forecast:
        control_forecast = [1.0]

    memo: Dict[Tuple[int, int, int, int, int, int, int], Tuple[int, List[str]]] = {}

    def key(st: State, i: int) -> Tuple[int, int, int, int, int, int, int]:
        return (
            st.qi,
            st.stability,
            st.completion,
            st.perfection,
            st.control_buff_turns,
            st.intensity_buff_turns,
            i,
        )

    def dfs(st: State, i: int) -> Tuple[int, List[str]]:
        k = key(st, i)
        if k in memo:
            return memo[k]

        # Stop early if targets are met
        if target_completion > 0 and target_perfection > 0:
            if st.targets_met(target_completion, target_perfection):
                res = (st.get_score(target_completion, target_perfection), [])
                memo[k] = res
                return res

        if i >= len(control_forecast) or optimizer.is_terminal(st):
            res = (st.get_score(target_completion, target_perfection), [])
            memo[k] = res
            return res

        best_val = -1
        best_plan: List[str] = []
        cond = control_forecast[i]

        for skill_key in optimizer.skills:
            ns = optimizer.apply_skill(st, skill_key, control_condition=cond)
            if ns is None:
                continue
            v, plan = dfs(ns, i + 1)
            if v > best_val:
                best_val = v
                best_plan = [skill_key] + plan

        if best_val < 0:
            res = (st.get_score(target_completion, target_perfection), [])
        else:
            res = (best_val, best_plan)
        memo[k] = res
        return res

    best_score, best_plan = dfs(state, 0)
    best_first = best_plan[0] if best_plan else None
    return best_first, best_plan, best_score


def _make_bar(
    current: int, maximum: int, width: int = 20, fill: str = "█", empty: str = "░"
) -> str:
    """Create a text-based progress bar."""
    if maximum <= 0:
        return empty * width
    ratio = min(current / maximum, 1.0)
    filled = int(ratio * width)
    return fill * filled + empty * (width - filled)


def _format_skill_details(
    optimizer: CraftingOptimizer,
    skill_key: str,
    state: State,
    control_condition: float = 1.0,
) -> str:
    """Format skill details showing costs and expected gains."""
    skill = optimizer.skills[skill_key]
    name, qi_cost, stability_cost, base_comp, base_perf, buff_type, buff_dur = skill

    parts = []

    # Qi cost
    if qi_cost > 0:
        parts.append(f"-{qi_cost} Qi")

    # Stability change
    if stability_cost > 0:
        parts.append(f"-{stability_cost} Stab")
    elif stability_cost < 0:
        parts.append(f"+{-stability_cost} Stab")

    comp_gain, perf_gain = optimizer.calculate_skill_gains(
        state, skill_key, control_condition=control_condition
    )
    if comp_gain > 0:
        parts.append(f"+{comp_gain} Comp")
    if perf_gain > 0:
        parts.append(f"+{perf_gain} Perf")

    # Buff
    if buff_type == BuffType.CONTROL:
        parts.append(f"[+40% Control x{buff_dur}]")
    elif buff_type == BuffType.INTENSITY:
        parts.append(f"[+40% Intensity x{buff_dur}]")

    return ", ".join(parts) if parts else "(no effect)"


def interactive_mode(
    optimizer: CraftingOptimizer, target_completion: int = 0, target_perfection: int = 0
):
    """Interactive mode: step through a craft session turn-by-turn.

    Each turn, the user inputs the next 4 control condition forecasts,
    the optimizer suggests the best action, and the user can accept or
    choose a different action. The state updates and the loop continues
    until no valid actions remain or targets are met.
    """
    state = State(
        qi=optimizer.max_qi,
        stability=optimizer.max_stability,
        max_stability=optimizer.max_stability,
        completion=0,
        perfection=0,
        control_buff_turns=0,
        intensity_buff_turns=0,
        history=[],
    )

    # Keep history of states for undo
    state_history = []
    # Keep history of forecasts for undo
    forecast_history = []
    # Current forecast (will be updated each turn)
    current_forecast = None

    turn = 1

    print()
    print("╔" + "═" * 68 + "╗")
    print("║" + " ASCEND FROM NINE MOUNTAINS - INTERACTIVE MODE ".center(68) + "║")
    print("╚" + "═" * 68 + "╝")
    print()
    print("┌" + "─" * 68 + "┐")
    print("│" + " COMMANDS ".center(68) + "│")
    print("├" + "─" * 68 + "┤")
    print("│  Turn 1:   Enter all 4 control multipliers (e.g. '1.5,1,0.5,1')  │")
    print("│  Turn 2+:  Previous forecast shifts; enter only the new T3 value │")
    print("│            Or enter 4 values to override, Enter for default      │")
    print("│                                                                  │")
    print("│  Actions:  Enter number or name to select skill                  │")
    print("│            Press Enter to accept suggestion                      │")
    print("│                                                                  │")
    print("│  Other:    'help' or 'h' - Show this help                        │")
    print("│            'undo' or 'u' - Undo last action                      │")
    print("│            'status' or 's' - Show detailed status                │")
    print("│            'quit' or 'q' - Exit interactive mode                 │")
    print("└" + "─" * 68 + "┘")
    print()

    def show_help():
        print()
        print("┌" + "─" * 68 + "┐")
        print("│" + " HELP ".center(68) + "│")
        print("├" + "─" * 68 + "┤")
        print("│  FORECAST INPUT                                                   │")
        print("│    Turn 1: Enter all 4 control conditions (current + next 3)     │")
        print("│    Turn 2+: Previous forecast shifts automatically:              │")
        print("│             T1→T0, T2→T1, T3→T2, then you enter new T3           │")
        print("│    • 1.5 = +50% control (good for perfection skills)              │")
        print("│    • 1.0 = normal control                                         │")
        print("│    • 0.5 = -50% control (bad for perfection skills)               │")
        print("│    You can also enter 4 values to override the entire forecast   │")
        print("│                                                                    │")
        print("│  SKILL SELECTION                                                  │")
        print("│    • Enter the number next to a skill to use it                   │")
        print("│    • Or type part of the skill name (e.g. 'simple' or 'fusion')   │")
        print("│    • Press Enter alone to accept the suggested action             │")
        print("│                                                                    │")
        print("│  GOAL                                                             │")
        if target_completion > 0 and target_perfection > 0:
            print(
                f"│    Reach Completion={target_completion}, Perfection={target_perfection}".ljust(
                    69
                )
                + "│"
            )
        else:
            print(
                "│    Maximize your Score = min(Completion, Perfection)              │"
            )
            print(
                "│    Keep both bars balanced for the best result!                   │"
            )
        print("│                                                                    │")
        print("│  COMMANDS: help, undo, status, quit                               │")
        print("└" + "─" * 68 + "┘")
        print()

    def show_status():
        print()
        print("┌" + "─" * 68 + "┐")
        print("│" + " DETAILED STATUS ".center(68) + "│")
        print("├" + "─" * 68 + "┤")
        print(
            f"│  Qi:         {state.qi:3d}/{optimizer.max_qi}  {_make_bar(state.qi, optimizer.max_qi, 30)}  │"
        )
        print(
            f"│  Stability:  {state.stability:3d}/{optimizer.max_stability}   {_make_bar(state.stability, optimizer.max_stability, 30)}  │"
        )
        if target_completion > 0 and target_perfection > 0:
            print(
                f"│  Completion: {state.completion:3d}/{target_completion:<3d}  "
                f"{_make_bar(state.completion, target_completion, 30)}  │"
            )
            print(
                f"│  Perfection: {state.perfection:3d}/{target_perfection:<3d}  "
                f"{_make_bar(state.perfection, target_perfection, 30)}  │"
            )
        else:
            comp_scale = max(100, state.completion)
            perf_scale = max(100, state.perfection)
            print(
                f"│  Completion: {state.completion:3d}      {_make_bar(state.completion, comp_scale, 30)}  │"
            )
            print(
                f"│  Perfection: {state.perfection:3d}      {_make_bar(state.perfection, perf_scale, 30)}  │"
            )
        print("├" + "─" * 68 + "┤")
        eff_intensity = state.get_intensity(optimizer.base_intensity)
        eff_control = state.get_control(optimizer.base_control)
        int_buff = " (+40% ACTIVE)" if state.intensity_buff_turns > 0 else ""
        ctrl_buff = " (+40% ACTIVE)" if state.control_buff_turns > 0 else ""
        print(
            f"│  Intensity: {optimizer.base_intensity} -> {eff_intensity}{int_buff}".ljust(
                69
            )
            + "│"
        )
        print(
            f"│  Control:   {optimizer.base_control} -> {eff_control}{ctrl_buff}".ljust(
                69
            )
            + "│"
        )
        if state.intensity_buff_turns > 0:
            print(
                f"│    Intensity buff: {state.intensity_buff_turns} turn(s) remaining".ljust(
                    69
                )
                + "│"
            )
        if state.control_buff_turns > 0:
            print(
                f"│    Control buff: {state.control_buff_turns} turn(s) remaining".ljust(
                    69
                )
                + "│"
            )
        print("├" + "─" * 68 + "┤")
        if target_completion > 0 and target_perfection > 0:
            if state.targets_met(target_completion, target_perfection):
                print(f"│  STATUS: ✓ TARGETS MET!".ljust(69) + "│")
            else:
                comp_remaining = max(0, target_completion - state.completion)
                perf_remaining = max(0, target_perfection - state.perfection)
                print(
                    f"│  REMAINING: Completion={comp_remaining}, Perfection={perf_remaining}".ljust(
                        69
                    )
                    + "│"
                )
        else:
            print(
                f"│  SCORE: {state.get_score()} (min of Completion and Perfection)".ljust(
                    69
                )
                + "│"
            )
        print("└" + "─" * 68 + "┘")
        if state.history:
            print()
            print("  Actions taken so far:")
            for i, action in enumerate(state.history, 1):
                print(f"    {i}. {action}")
        print()

    # Build skill list for selection
    skill_keys = list(optimizer.skills.keys())

    while not optimizer.is_terminal(state):
        # Check if targets are met
        if target_completion > 0 and target_perfection > 0:
            if state.targets_met(target_completion, target_perfection):
                print("\n  ✓ TARGETS MET! Ending craft session.")
                break

        # Turn header
        print("┌" + "─" * 68 + "┐")
        print("│" + f" TURN {turn} ".center(68) + "│")
        print("└" + "─" * 68 + "┘")

        # Compact status display
        qi_bar = _make_bar(state.qi, optimizer.max_qi, 15)
        stab_bar = _make_bar(state.stability, optimizer.max_stability, 15)
        print(
            f"  Qi: {state.qi:3d}/{optimizer.max_qi} {qi_bar}   Stability: {state.stability:2d}/{optimizer.max_stability} {stab_bar}"
        )
        if target_completion > 0 and target_perfection > 0:
            print(
                f"  Completion: {state.completion:3d}/{target_completion}                 Perfection: {state.perfection:3d}/{target_perfection}"
            )
            comp_remaining = max(0, target_completion - state.completion)
            perf_remaining = max(0, target_perfection - state.perfection)
            print(f"  ══► REMAINING: Comp={comp_remaining}, Perf={perf_remaining}")
        else:
            print(
                f"  Completion: {state.completion:3d}                    Perfection: {state.perfection:3d}"
            )
            print(f"  ══► SCORE: {state.get_score()}")

        # Show active buffs inline
        buffs = []
        if state.control_buff_turns > 0:
            buffs.append(f"Control +40% ({state.control_buff_turns}t)")
        if state.intensity_buff_turns > 0:
            buffs.append(f"Intensity +40% ({state.intensity_buff_turns}t)")
        if buffs:
            print(f"  Active Buffs: {', '.join(buffs)}")
        print()

        # Ask for forecast FIRST (player sees conditions before selecting skills)
        # On turn 1, ask for all 4 values. On subsequent turns, shift and ask for new T3.
        control_forecast = None
        while True:
            if current_forecast is None:
                # First turn: ask for all 4 values
                prompt = "► Forecast (e.g. '1.5,1,0.5,1') [Enter=default]: "
            else:
                # Subsequent turns: show shifted forecast and ask for new T3
                shifted = current_forecast[1:4]  # T1, T2, T3 become T0, T1, T2
                shifted_desc = []
                for i, m in enumerate(shifted):
                    if m > 1:
                        shifted_desc.append(f"+{int((m - 1) * 100)}%")
                    elif m < 1:
                        shifted_desc.append(f"{int((m - 1) * 100)}%")
                    else:
                        shifted_desc.append("1")
                print(
                    f"  Previous forecast shifted: T0={shifted_desc[0]}, T1={shifted_desc[1]}, T2={shifted_desc[2]}"
                )
                prompt = (
                    "► New T3 value (e.g. '1.5') [Enter=1, or 4 values to override]: "
                )

            try:
                forecast_input = input(prompt).strip()
            except EOFError:
                print("\n  Goodbye!")
                return

            if forecast_input.lower() in ("quit", "q"):
                print("\n  Goodbye!")
                return

            if forecast_input.lower() in ("help", "h"):
                show_help()
                continue

            if forecast_input.lower() in ("status", "s"):
                show_status()
                continue

            if forecast_input.lower() in ("undo", "u"):
                if state_history:
                    state = state_history.pop()
                    current_forecast = (
                        forecast_history.pop() if forecast_history else None
                    )
                    turn -= 1
                    print(f"  ↩ Undone! Back to turn {turn}.")
                    print()
                    control_forecast = None  # Signal to redo turn
                    break
                else:
                    print("  Nothing to undo.")
                continue

            if not forecast_input:
                if current_forecast is None:
                    # First turn default
                    control_forecast = [1.0, 1.0, 1.0, 1.0]
                else:
                    # Subsequent turns: shift and add default T3=1.0
                    control_forecast = current_forecast[1:4] + [1.0]
                break

            try:
                parsed = _parse_control_forecast(forecast_input)
                if len(parsed) == 1 and current_forecast is not None:
                    # Single value: use as new T3, shift the rest
                    control_forecast = current_forecast[1:4] + parsed
                    break
                elif len(parsed) == 4:
                    # Full override with 4 values
                    control_forecast = parsed
                    break
                elif current_forecast is None:
                    print("  ✗ Please enter exactly 4 values for the first turn.")
                    continue
                else:
                    print("  ✗ Enter 1 value (new T3) or 4 values (full override).")
                    continue
            except argparse.ArgumentTypeError as e:
                print(f"  ✗ Invalid input: {e}")
                continue

        # Handle undo from forecast prompt
        if control_forecast is None:
            continue

        # Show forecast interpretation if not default
        if control_forecast != [1.0, 1.0, 1.0, 1.0]:
            forecast_desc = []
            for i, m in enumerate(control_forecast):
                if m > 1:
                    forecast_desc.append(f"T{i}: +{int((m - 1) * 100)}%")
                elif m < 1:
                    forecast_desc.append(f"T{i}: {int((m - 1) * 100)}%")
                else:
                    forecast_desc.append(f"T{i}: normal")
            print(f"  Forecast: {' │ '.join(forecast_desc)}")
            print()

        # Get suggestion using the provided forecast
        best_first, plan, horizon_score = suggest_next_turn(
            optimizer, state, control_forecast, target_completion, target_perfection
        )

        if best_first is None:
            print("\n  No valid action found from this state.")
            break

        # Show suggestion with box
        print("  ┌" + "─" * 50 + "┐")
        print(f"  │ ★ SUGGESTED: {optimizer.skills[best_first][0]}".ljust(52) + "│")
        print(
            f"  │   {_format_skill_details(optimizer, best_first, state, control_forecast[0])}".ljust(
                52
            )
            + "│"
        )
        print("  └" + "─" * 50 + "┘")

        if plan and len(plan) > 1:
            if target_completion > 0 and target_perfection > 0:
                print(
                    f"\n  Lookahead plan ({len(plan)} turns, progress: {horizon_score}/{target_completion + target_perfection}):"
                )
            else:
                print(
                    f"\n  Lookahead plan ({len(plan)} turns, expected score: {horizon_score}):"
                )
            for i, k in enumerate(plan, 1):
                marker = "→" if i == 1 else " "
                print(f"    {marker} {i}. {optimizer.skills[k][0]}")
            print()
        else:
            print()

        # Show available skills with details
        print("  Available skills:")
        print("  " + "─" * 60)
        valid_skills = []
        for i, sk in enumerate(skill_keys, 1):
            test_state = optimizer.apply_skill(
                state, sk, control_condition=control_forecast[0]
            )
            if test_state is not None:
                skill_info = optimizer.skills[sk]
                valid_skills.append((i, sk))
                marker = " ★" if sk == best_first else "  "
                details = _format_skill_details(
                    optimizer, sk, state, control_forecast[0]
                )
                print(f"  {marker} {i}. {skill_info[0]:<22} {details}")
        print("  " + "─" * 60)

        if not valid_skills:
            print("\n  No valid actions available.")
            break

        # Get user choice
        redo_turn = False
        chosen_key = None
        while True:
            try:
                choice = input("\n► Select skill [Enter=accept suggestion]: ").strip()
            except EOFError:
                print("\n  Goodbye!")
                return

            if choice.lower() in ("quit", "q"):
                print("\n  Goodbye!")
                return

            if choice.lower() in ("help", "h"):
                show_help()
                continue

            if choice.lower() in ("status", "s"):
                show_status()
                continue

            if choice.lower() in ("undo", "u"):
                if state_history:
                    state = state_history.pop()
                    current_forecast = (
                        forecast_history.pop() if forecast_history else None
                    )
                    turn -= 1
                    print(f"  ↩ Undone! Back to turn {turn}.")
                    redo_turn = True
                    break  # Will re-display the turn
                else:
                    print("  Nothing to undo.")
                continue

            if not choice:
                # Accept suggestion
                chosen_key = best_first
                break

            # Try to parse as number
            try:
                num = int(choice)
                # Find the skill by number
                found = False
                for idx, sk in valid_skills:
                    if idx == num:
                        chosen_key = sk
                        found = True
                        break
                if found:
                    break
                else:
                    print(f"  ✗ Invalid number. Choose from the list above.")
            except ValueError:
                # Try to match by name
                choice_lower = choice.lower()
                matches = []
                for idx, sk in valid_skills:
                    if (
                        choice_lower in optimizer.skills[sk][0].lower()
                        or choice_lower == sk
                    ):
                        matches.append((idx, sk))
                if len(matches) == 1:
                    chosen_key = matches[0][1]
                    break
                elif len(matches) > 1:
                    print(f"  ✗ Ambiguous: '{choice}' matches multiple skills:")
                    for idx, sk in matches:
                        print(f"      {idx}. {optimizer.skills[sk][0]}")
                    print(f"    Please enter the number to select.")
                else:
                    print(f"  ✗ No skill matching '{choice}'. Try again.")

        if redo_turn:
            continue

        # Apply the chosen skill
        new_state = optimizer.apply_skill(
            state, chosen_key, control_condition=control_forecast[0]
        )
        if new_state is None:
            print(
                f"\n  ✗ Error: Could not apply {optimizer.skills[chosen_key][0]}. This shouldn't happen."
            )
            break

        # Save state and forecast for undo
        state_history.append(state)
        forecast_history.append(current_forecast)

        # Show what happened
        skill_name = optimizer.skills[chosen_key][0]
        comp_gain = new_state.completion - state.completion
        perf_gain = new_state.perfection - state.perfection
        qi_cost = state.qi - new_state.qi
        stab_change = new_state.stability - state.stability

        print()
        print("  ╔" + "═" * 50 + "╗")
        print(f"  ║ ✓ APPLIED: {skill_name}".ljust(52) + "║")
        changes = []
        if qi_cost > 0:
            changes.append(f"Qi -{qi_cost}")
        if stab_change > 0:
            changes.append(f"Stab +{stab_change}")
        elif stab_change < 0:
            changes.append(f"Stab {stab_change}")
        if comp_gain > 0:
            changes.append(f"Comp +{comp_gain}")
        if perf_gain > 0:
            changes.append(f"Perf +{perf_gain}")
        if changes:
            print(f"  ║   {' │ '.join(changes)}".ljust(52) + "║")
        print("  ╚" + "═" * 50 + "╝")

        state = new_state
        current_forecast = control_forecast  # Save for next turn's shift
        turn += 1
        print()

    # Final summary
    print()
    print("╔" + "═" * 68 + "╗")
    print("║" + " CRAFT COMPLETE ".center(68) + "║")
    print("╚" + "═" * 68 + "╝")
    print()
    print("┌" + "─" * 68 + "┐")
    print("│" + " FINAL RESULTS ".center(68) + "│")
    print("├" + "─" * 68 + "┤")
    print(f"│  Qi Remaining:  {state.qi:3d}/{optimizer.max_qi}".ljust(69) + "│")
    print(
        f"│  Stability:     {state.stability:3d}/{optimizer.max_stability}".ljust(69)
        + "│"
    )
    print("├" + "─" * 68 + "┤")
    if target_completion > 0 and target_perfection > 0:
        comp_bar = _make_bar(state.completion, target_completion, 30)
        perf_bar = _make_bar(state.perfection, target_perfection, 30)
        print(
            f"│  Completion:    {state.completion:3d}/{target_completion}  {comp_bar}".ljust(
                69
            )
            + "│"
        )
        print(
            f"│  Perfection:    {state.perfection:3d}/{target_perfection}  {perf_bar}".ljust(
                69
            )
            + "│"
        )
    else:
        print(
            f"│  Completion:    {state.completion:3d}  {_make_bar(state.completion, 100, 30)}".ljust(
                69
            )
            + "│"
        )
        print(
            f"│  Perfection:    {state.perfection:3d}  {_make_bar(state.perfection, 100, 30)}".ljust(
                69
            )
            + "│"
        )
    print("├" + "─" * 68 + "┤")
    if target_completion > 0 and target_perfection > 0:
        if state.targets_met(target_completion, target_perfection):
            print(f"│  ★ TARGETS MET!".ljust(69) + "│")
        else:
            comp_remaining = max(0, target_completion - state.completion)
            perf_remaining = max(0, target_perfection - state.perfection)
            print(f"│  ✗ Targets not fully reached".ljust(69) + "│")
            print(
                f"│    Remaining: Completion={comp_remaining}, Perfection={perf_remaining}".ljust(
                    69
                )
                + "│"
            )
    else:
        score = state.get_score()
        print(f"│  ★ FINAL SCORE: {score}".ljust(69) + "│")
        if state.completion != state.perfection:
            diff = abs(state.completion - state.perfection)
            lower = (
                "Completion" if state.completion < state.perfection else "Perfection"
            )
            print(f"│    (Limited by {lower}, {diff} points behind)".ljust(69) + "│")
    print("└" + "─" * 68 + "┘")

    if state.history:
        print()
        print(f"  Actions taken ({len(state.history)} total):")
        for i, action in enumerate(state.history, 1):
            print(f"    {i}. {action}")
    print()


def main():
    parser = argparse.ArgumentParser(
        description="Ascend From Nine Mountains - Crafting Optimizer"
    )
    parser.add_argument(
        "--config",
        type=str,
        default=None,
        help=(
            "Path to JSON configuration file for stats and skills. "
            "If not provided, loads ./config.json when present, otherwise uses embedded defaults."
        ),
    )
    parser.add_argument(
        "-f",
        "--forecast-control",
        type=_parse_control_forecast,
        default=None,
        help=(
            "Comma-separated per-turn control multipliers (current turn first), e.g. '1.5,1,0.5,1'. "
            "Applied to Control-scaling skills only."
        ),
    )
    parser.add_argument(
        "-s",
        "--suggest-next",
        action="store_true",
        help="Suggest the best next action using lookahead over --forecast-control.",
    )
    parser.add_argument(
        "-i",
        "--interactive",
        action="store_true",
        help="Run in interactive mode: step through a craft session turn-by-turn.",
    )
    parser.add_argument(
        "-c",
        "--target-completion",
        type=int,
        default=0,
        help="Target completion value to reach. Required with -p/--target-perfection.",
    )
    parser.add_argument(
        "-p",
        "--target-perfection",
        type=int,
        default=0,
        help="Target perfection value to reach. Required with -c/--target-completion.",
    )
    parser.add_argument(
        "-t",
        "--targets",
        nargs=2,
        type=int,
        metavar=("COMPLETION", "PERFECTION"),
        help="Shorthand for targets: -t 60 60 is equivalent to -c 60 -p 60.",
    )
    args = parser.parse_args()

    # Handle -t/--targets shorthand
    if args.targets:
        if args.target_completion > 0 or args.target_perfection > 0:
            raise SystemExit(
                "Cannot use -t/--targets together with -c/--target-completion or -p/--target-perfection."
            )
        args.target_completion, args.target_perfection = args.targets

    # Validate targets - both must be provided together
    if (args.target_completion > 0) != (args.target_perfection > 0):
        raise SystemExit(
            "Both -c/--target-completion and -p/--target-perfection must be provided together (or use -t)."
        )

    optimizer = CraftingOptimizer(config_path=args.config)

    print("=" * 70)
    print("ASCEND FROM NINE MOUNTAINS - CRAFTING OPTIMIZER")
    print("=" * 70)
    print(f"\nYour Stats:")
    print(f"  Max Qi: {optimizer.max_qi}")
    print(f"  Max Stability: {optimizer.max_stability}")
    print(f"  Intensity: {optimizer.base_intensity} (affects completion)")
    print(f"  Control: {optimizer.base_control} (affects perfection)")
    print(f"\nRules:")
    print(f"  - Most actions cost stability; see skills/config for exact costs")
    print(
        f"  - Stability must stay >= {optimizer.min_stability} (restore before dropping below)"
    )
    if args.target_completion > 0 and args.target_perfection > 0:
        print(
            f"  - Goal: Reach Completion={args.target_completion}, Perfection={args.target_perfection}"
        )
    else:
        print(f"  - Goal: Maximize min(Completion, Perfection)")
    print()

    if args.interactive:
        interactive_mode(optimizer, args.target_completion, args.target_perfection)
        return

    if args.suggest_next:
        if not args.forecast_control:
            raise SystemExit(
                "--suggest-next requires --forecast-control, e.g. --forecast-control '1.5,1,0.5,1'"
            )

        if len(args.forecast_control) != 4:
            raise SystemExit(
                "--suggest-next expects exactly 4 comma-separated values for --forecast-control "
                "(current turn + next 3), e.g. --forecast-control '1.5,1,0.5,1'"
            )

        start_state = State(
            qi=optimizer.max_qi,
            stability=optimizer.max_stability,
            max_stability=optimizer.max_stability,
            completion=0,
            perfection=0,
            control_buff_turns=0,
            intensity_buff_turns=0,
            history=[],
        )

        best_first, plan, horizon_score = suggest_next_turn(
            optimizer,
            start_state,
            args.forecast_control,
            args.target_completion,
            args.target_perfection,
        )
        print("=" * 70)
        print("NEXT-TURN SUGGESTION")
        print("=" * 70)
        print(
            f"\nControl forecast: {', '.join(f'x{m:g}' for m in args.forecast_control)}"
        )
        if args.target_completion > 0 and args.target_perfection > 0:
            print(
                f"Targets: Completion={args.target_completion}, Perfection={args.target_perfection}"
            )
        if best_first is None:
            print("\nNo valid action found from this state.")
            return
        print(f"\nBest next action: {optimizer.skills[best_first][0]}")
        if plan:
            print(f"Best {len(plan)}-turn plan (within forecast horizon):")
            for i, k in enumerate(plan, 1):
                print(f"  {i}. {optimizer.skills[k][0]}")
            optimizer.print_detailed_rotation(
                plan,
                target_completion=args.target_completion,
                target_perfection=args.target_perfection,
                control_conditions=args.forecast_control,
            )
        if args.target_completion > 0 and args.target_perfection > 0:
            print(
                f"\nHorizon progress after lookahead: {horizon_score}/{args.target_completion + args.target_perfection}"
            )
        else:
            print(f"\nHorizon score (min) after lookahead: {horizon_score}")
        return

    print("=" * 70)
    print("SEARCHING FOR OPTIMAL ROTATION...")
    print("=" * 70)

    # Exhaustive search for optimal
    print("\nRunning exhaustive search (this may take a moment)...")
    optimal_state = optimizer.search_optimal(
        args.target_completion, args.target_perfection
    )

    print("\n" + "-" * 70)
    print("OPTIMAL ROTATION FOUND")
    print("-" * 70)
    optimizer.print_state(optimal_state, args.target_completion, args.target_perfection)

    # Get skill keys from history names for detailed breakdown
    rotation_keys = []
    for name in optimal_state.history:
        rotation_keys.append(optimizer.get_skill_key_from_name(name))

    optimizer.print_detailed_rotation(
        rotation_keys,
        target_completion=args.target_completion,
        target_perfection=args.target_perfection,
    )

    # Also run greedy for comparison
    print("\n" + "-" * 70)
    print("GREEDY SEARCH (for comparison)")
    print("-" * 70)
    greedy_state = optimizer.greedy_search(
        args.target_completion, args.target_perfection
    )
    optimizer.print_state(greedy_state, args.target_completion, args.target_perfection)

    # Final recommendation
    print("\n" + "=" * 70)
    print("RECOMMENDED SKILL ROTATION")
    print("=" * 70)
    if args.target_completion > 0 and args.target_perfection > 0:
        if optimal_state.targets_met(args.target_completion, args.target_perfection):
            print(f"\n✓ TARGETS MET!")
        else:
            print(f"\n✗ Targets not fully reached")
        print(
            f"Target Completion: {args.target_completion}, Achieved: {optimal_state.completion}"
        )
        print(
            f"Target Perfection: {args.target_perfection}, Achieved: {optimal_state.perfection}"
        )
    else:
        print(
            f"\nBest Score: {optimal_state.get_score()} (min of Completion and Perfection)"
        )
        print(f"Final Completion: {optimal_state.completion}")
        print(f"Final Perfection: {optimal_state.perfection}")
    print(f"\nUse these skills in order:")
    for i, action in enumerate(optimal_state.history, 1):
        print(f"  {i}. {action}")


if __name__ == "__main__":
    main()
