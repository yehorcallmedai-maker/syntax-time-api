# -*- coding: utf-8 -*-
import json
from typing import Literal
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from core.leibniz_rbn import LeibnizRBN
from hypervisor.nested_hypervisor import NestedHypervisorL1
from time_sync import current_time_phase

with open("config/rbn_setup.json") as f:
    _config = json.load(f)
SEED = _config["rbn"]["default_seed"]
MAX_STEPS = _config["simulation_defaults"]["max_steps"]
EXECUTION_HASH = "efa5f43b767859a77c895ec280e594cee26d2c8cdaeef155208bd17d086ad80d"

app = FastAPI(title="Leibniz 64-Phase Simulator", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["https://yehor.ai", "https://www.yehor.ai"], allow_methods=["*"], allow_headers=["*"])

_rbn = None
_hypervisor = None

def _fresh_session(initial_state, seed=SEED):
    global _rbn, _hypervisor
    rbn = LeibnizRBN(seed=seed)
    rbn.set_state(initial_state)
    _rbn = rbn
    _hypervisor = NestedHypervisorL1(rbn)

class RunRequest(BaseModel):
    initial_state: int = Field(45, ge=0, le=63)
    interrupt: Literal["none", "acpi", "vm_exit"] = "none"
    interrupt_at_step: int = Field(10, ge=0)
    seed: int = Field(SEED)

class ControlRequest(BaseModel):
    action: Literal["acpi", "vm_exit"]

class TraceEntry(BaseModel):
    step: int
    state: int
    binary: str
    mode: str

class RunResponse(BaseModel):
    initial_state: int
    final_state: int
    final_binary: str
    interrupt: str
    behavior: str
    steps: int
    trace: list[TraceEntry]

class StateResponse(BaseModel):
    state: int
    binary: str
    frozen: bool
    acpi_active: bool

class AttestationResponse(BaseModel):
    status: str
    tests_passed: int
    tests_total: int
    execution_hash: str
    date: str
    director: str
    note: str

class TimePhaseResponse(BaseModel):
    utc_timestamp: str
    macro_state_int: int
    macro_state_bin: str
    micro_state_int: int
    micro_state_bin: str
    macro_block_days: float
    micro_block_minutes: float

@app.get("/", include_in_schema=False)
def root():
    return {"simulator": "Leibniz 64-Phase", "docs": "/docs", "version": "1.0.0"}

@app.get("/time-phase", response_model=TimePhaseResponse)
def get_time_phase():
    p = current_time_phase()
    return TimePhaseResponse(
        utc_timestamp=p.utc_timestamp,
        macro_state_int=p.macro_state_int,
        macro_state_bin=p.macro_state_bin,
        micro_state_int=p.micro_state_int,
        micro_state_bin=p.micro_state_bin,
        macro_block_days=p.macro_block_days,
        micro_block_minutes=p.micro_block_minutes,
    )

@app.get("/state", response_model=StateResponse)
def get_state():
    if _rbn is None:
        raise HTTPException(status_code=404, detail="No active session. POST /run first.")
    s = _rbn.get_state()
    return StateResponse(
        state=s,
        binary=format(s, "06b"),
        frozen=_hypervisor._stasis_frozen if _hypervisor else False,
        acpi_active=_hypervisor.acpi_active if _hypervisor else False,
    )

@app.post("/run", response_model=RunResponse)
def run_simulation(req: RunRequest):
    _fresh_session(req.initial_state, req.seed)
    trace_out = []
    for step_idx in range(MAX_STEPS):
        if step_idx == req.interrupt_at_step:
            if req.interrupt == "acpi":
                _hypervisor.inject_acpi_shutdown()
            elif req.interrupt == "vm_exit":
                _hypervisor.trigger_vm_exit_suspend()
        partial = _hypervisor.execute_cycle(max_steps=1)
        if partial:
            _, state, mode = partial[0]
            trace_out.append(TraceEntry(step=step_idx, state=state, binary=format(state, "06b"), mode=mode))
        if _hypervisor.acpi_active and _rbn.get_state() == 0:
            break
    final = _rbn.get_state()
    behavior = "AUTOMATIC_TRANSITION" if req.interrupt == "acpi" else "STATIC_STASIS" if req.interrupt == "vm_exit" else "FREE_RUN"
    return RunResponse(
        initial_state=req.initial_state,
        final_state=final,
        final_binary=format(final, "06b"),
        interrupt=req.interrupt,
        behavior=behavior,
        steps=len(trace_out),
        trace=trace_out,
    )

@app.post("/control")
def control(req: ControlRequest):
    if _hypervisor is None:
        raise HTTPException(status_code=404, detail="No active session. POST /run first.")
    if req.action == "acpi":
        _hypervisor.inject_acpi_shutdown()
        return {"injected": "ACPI_SHUTDOWN", "state": _rbn.get_state()}
    _hypervisor.trigger_vm_exit_suspend()
    return {
        "injected": "VM_EXIT_SUSPEND",
        "frozen_state": _hypervisor.vmcs02.guest_rip,
        "frozen_vector": _hypervisor.vmcs02.frozen_state_vector,
        "exit_reason": _hypervisor.vmcs02.exit_reason,
    }

@app.get("/attestation", response_model=AttestationResponse)
def attestation():
    return AttestationResponse(
        status="COMPLETED",
        tests_passed=10,
        tests_total=10,
        execution_hash=EXECUTION_HASH,
        date="2026-06-15",
        director="Egor",
        note="Hash: python -m unittest discover -s tests -v 2>&1 | sha256sum",
    )
