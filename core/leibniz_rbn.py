# -*- coding: utf-8 -*-
"""
Leibniz 64-Phase RBN Engine
KS-TRACE: core module | assumption: N=6 maps exactly to 64 Shao Yong hexagram states
"""

import numpy as np


class LeibnizRBN:
    """
    Random Boolean Network (Kauffman) with N=6 nodes, K=2 connectivity.
    State space: {0,1}^6 → 64 discrete phases (Shao Yong Xiantiantu order).
    Langton Lambda = 0.5 achieved by exactly 2 ones in each 4-entry truth table.

    #KS-TRACE: REQ-01 | assumption: States map to 64 discrete integers | test: test_state_space_bounds
    """

    N = 6
    NUM_STATES = 64  # 2^6

    def __init__(self, seed: int = 1701):
        self.state = np.zeros(self.N, dtype=np.int8)
        rng = np.random.default_rng(seed)

        # #KS-TRACE: REQ-02 | assumption: K=2 connectivity yields phase-transition capability | test: test_criticality_parameter
        self.K = 2
        self.connections: dict[int, np.ndarray] = {}
        self.truth_tables: dict[int, np.ndarray] = {}

        for i in range(self.N):
            # Each node receives signals from exactly 2 distinct nodes
            self.connections[i] = rng.choice(self.N, self.K, replace=False)
            # λ=0.5: exactly 2 ones out of 4 entries
            table = np.array([0, 0, 1, 1], dtype=np.int8)
            self.truth_tables[i] = rng.permutation(table)

    # ------------------------------------------------------------------ #
    def set_state(self, decimal_val: int) -> None:
        """Load a decimal state index (0–63) into the node vector."""
        if not (0 <= decimal_val < self.NUM_STATES):
            raise ValueError(f"State index must be in [0, 63], got {decimal_val}")
        binary_str = format(decimal_val, f'0{self.N}b')
        self.state = np.array([int(c) for c in binary_str], dtype=np.int8)

    def get_state(self) -> int:
        """Return current state as a decimal integer."""
        return int("".join(self.state.astype(str)), 2)

    # #KS-TRACE: REQ-03 | assumption: Synchronous update preserves deterministic trajectory | test: test_trajectory_reproducibility
    def step(self) -> int:
        """Advance simulation by one synchronous tick. Returns new decimal state."""
        new_state = np.zeros(self.N, dtype=np.int8)
        for i in range(self.N):
            inputs = self.state[self.connections[i]]
            table_idx = int("".join(inputs.astype(str)), 2)
            new_state[i] = self.truth_tables[i][table_idx]
        self.state = new_state
        state_val = self.get_state()
        # Invariant guard — should never trigger given N=6
        assert 0 <= state_val < self.NUM_STATES, f"Invariant violated: state={state_val}"
        return state_val
