# -*- coding: utf-8 -*-
"""
Nested Hypervisor L1 — Clock Intercept Layer
Architecture:
  L0 — Physical host (bare-metal)
  L1 — Architect hypervisor (this module)
  L2 — Guest simulation (LeibnizRBN)

Two interrupt pathways:
  ACPI_SHUTDOWN   → Graceful entropic descent to state 0 (Yin/Kun hexagram)
  VM_EXIT_SUSPEND → Instant VMCS freeze, time suspended indefinitely

#KS-TRACE: REQ-04 | assumption: L1 controls L2 execution clock | test: test_shutdown_pathways
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Literal

from core.leibniz_rbn import LeibnizRBN

TraceMode = Literal["ACTIVE", "ACPI_DECAY", "STASIS_FREEZE"]
TraceEntry = tuple[int, int, TraceMode]


@dataclass
class VMCS02:
    """Shadow VMCS structure — captures L2 state on VM-Exit before clock halt.
    Fix for KS-ERR-01 (race condition): state is snapshotted atomically
    before any further mutation.
    """
    guest_rip: int = 0
    frozen_state_vector: list[int] = field(default_factory=list)
    exit_reason: str = ""


class NestedHypervisorL1:
    """
    #KS-TRACE: REQ-04 | assumption: VM-Exit intercept prevents VMRESUME | test: test_vm_exit_freeze
    #KS-TRACE: REQ-05 | assumption: ACPI forces node-by-node decay to Kun (000000) | test: test_acpi_decay_to_zero
    """

    def __init__(self, rbn: LeibnizRBN):
        self.rbn = rbn
        self.vmcs02 = VMCS02()

        self._stasis_frozen: bool = False
        self._acpi_triggered: bool = False
        self._acpi_decay_step: int = 0

    # ------------------------------------------------------------------ #
    # Control plane — interrupt injection
    # ------------------------------------------------------------------ #

    def inject_acpi_shutdown(self) -> None:
        """Graceful shutdown: begin entropic descent toward Kun (state 0)."""
        self._acpi_triggered = True

    def trigger_vm_exit_suspend(self) -> None:
        """
        Hardware suspension via VM-Exit.
        KS-ERR-01 fix: snapshot state into VMCS02 *before* halting clock.
        """
        # Atomic snapshot — prevents race between compute and freeze
        self.vmcs02.frozen_state_vector = self.rbn.state.tolist()
        self.vmcs02.guest_rip = self.rbn.get_state()
        self.vmcs02.exit_reason = "EXIT_REASON_HLT"
        self._stasis_frozen = True

    # ------------------------------------------------------------------ #
    # Execution loop
    # ------------------------------------------------------------------ #

    def execute_cycle(self, max_steps: int = 100) -> list[TraceEntry]:
        """
        Run up to max_steps ticks of L2 simulation under L1 control.

        Returns a trace list of (step_index, decimal_state, mode).
        Halts early when ACPI decay reaches state 0 or stasis is frozen.
        """
        trace: list[TraceEntry] = []

        for step_idx in range(max_steps):

            # ---- STASIS path: time is frozen ----
            if self._stasis_frozen:
                current_state = self.rbn.get_state()
                trace.append((step_idx, current_state, "STASIS_FREEZE"))
                # VMRESUME is blocked — do not advance
                continue

            # ---- ACPI path: entropic descent ----
            if self._acpi_triggered:
                # #KS-TRACE: REQ-05 | ACPI has highest priority, overrides attractor pull
                if self._acpi_decay_step < self.rbn.N:
                    # Zero out nodes one by one (Yin descent)
                    self.rbn.state[self._acpi_decay_step] = 0
                    self._acpi_decay_step += 1

                current_state = self.rbn.get_state()
                trace.append((step_idx, current_state, "ACPI_DECAY"))

                if current_state == 0:
                    break  # Kun reached — harmonia praestabilita restored
                continue

            # ---- ACTIVE path: normal harmonic tick ----
            current_state = self.rbn.step()
            trace.append((step_idx, current_state, "ACTIVE"))

        return trace

    # ------------------------------------------------------------------ #
    # Diagnostics
    # ------------------------------------------------------------------ #

    @property
    def is_frozen(self) -> bool:
        return self._stasis_frozen

    @property
    def acpi_active(self) -> bool:
        return self._acpi_triggered
