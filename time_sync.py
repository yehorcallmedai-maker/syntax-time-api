# -*- coding: utf-8 -*-
"""
time_sync.py — SYNTAX // TIME
Temporal Synchronization Layer for the Leibniz 64-Phase Simulator.

Maps real-world UTC time to the 64-phase binary state space {0…63}.

  Macro Phase (Calendar):
    365.24 solar days ÷ 64 = 5.70688 days per phase block.
    Measures current day-of-year position relative to Jan 1 00:00:00 UTC.

  Micro Phase (Clock):
    1440 minutes per day ÷ 64 = 22.5 minutes per phase block.
    Measures current minute-of-day position relative to midnight UTC.

#KS-TRACE: REQ-TIME-01 | assumption: UTC epoch anchor is Jan 1 00:00:00 of current year
           | test: deterministic_given_fixed_utc_timestamp
"""

from __future__ import annotations
from datetime import datetime, timezone, date
from dataclasses import dataclass

# ── Constants ─────────────────────────────────────────────────────────────────

NUM_PHASES: int = 64
SOLAR_YEAR_DAYS: float = 365.24
MACRO_BLOCK_DAYS: float = SOLAR_YEAR_DAYS / NUM_PHASES   # 5.70688 days
MINUTES_PER_DAY: int = 1440
MICRO_BLOCK_MINUTES: float = MINUTES_PER_DAY / NUM_PHASES  # 22.5 minutes


# ── Output schema ─────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class TimePhase:
    utc_timestamp: str       # ISO 8601
    macro_state_int: int     # 0–63 — calendar position
    macro_state_bin: str     # 6-bit binary string
    micro_state_int: int     # 0–63 — clock position
    micro_state_bin: str     # 6-bit binary string
    macro_block_days: float  # block width in days (5.70688…)
    micro_block_minutes: float  # block width in minutes (22.5)


# ── Core computation ──────────────────────────────────────────────────────────

def current_time_phase(utc_now: datetime | None = None) -> TimePhase:
    """
    Compute the current macro and micro phase from UTC time.

    Args:
        utc_now: override for testing; defaults to datetime.now(timezone.utc)

    Returns:
        TimePhase dataclass with all phase data.

    #KS-TRACE: REQ-TIME-01 | assumption: leap-year seconds ignored at macro scale
               | test: macro_phase_boundary_jan1, micro_phase_boundary_midnight
    """
    if utc_now is None:
        utc_now = datetime.now(timezone.utc)

    # ── Macro: day-of-year → phase block ─────────────────────────────────────
    year_start = datetime(utc_now.year, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    day_of_year: float = (utc_now - year_start).total_seconds() / 86400.0
    macro_state: int = min(int(day_of_year / MACRO_BLOCK_DAYS), NUM_PHASES - 1)

    # ── Micro: minute-of-day → phase block ───────────────────────────────────
    minute_of_day: float = utc_now.hour * 60 + utc_now.minute + utc_now.second / 60.0
    micro_state: int = min(int(minute_of_day / MICRO_BLOCK_MINUTES), NUM_PHASES - 1)

    return TimePhase(
        utc_timestamp=utc_now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        macro_state_int=macro_state,
        macro_state_bin=format(macro_state, "06b"),
        micro_state_int=micro_state,
        micro_state_bin=format(micro_state, "06b"),
        macro_block_days=round(MACRO_BLOCK_DAYS, 5),
        micro_block_minutes=MICRO_BLOCK_MINUTES,
    )


# ── CLI smoke-test ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    phase = current_time_phase()
    print(f"UTC          : {phase.utc_timestamp}")
    print(f"Macro phase  : {phase.macro_state_int:>2d}  ({phase.macro_state_bin})  "
          f"[block {phase.macro_state_int + 1}/64 · {phase.macro_block_days} days each]")
    print(f"Micro phase  : {phase.micro_state_int:>2d}  ({phase.micro_state_bin})  "
          f"[block {phase.micro_state_int + 1}/64 · {phase.micro_block_minutes} min each]")
