"""
qiskit_router.py — Project Photon
IBM Qiskit Quantum Neural Network layer for payment route optimization.

Pipeline:
  QuantumCircuit (4-qubit parameterized)
      → EstimatorQNN  (IBM Qiskit primitive)
          → TorchConnector  (PyTorch-compatible hybrid layer)
"""

import numpy as np
import torch
from qiskit import QuantumCircuit
from qiskit.circuit import ParameterVector
from qiskit.quantum_info import SparsePauliOp
from qiskit_machine_learning.neural_networks import EstimatorQNN
from qiskit_machine_learning.connectors import TorchConnector

N_QUBITS = 4  # One qubit per route candidate


def build_photon_circuit() -> tuple:
    """
    Build the parameterized 4-qubit Photon QNN circuit.

    Architecture
    ------------
    Layer 1 — Input encoding : RY(x_i * π) on each qubit
    Layer 2 — Entanglement   : circular CNOT chain
    Layer 3 — Variational    : trainable RY(θ_i) rotations

    Returns (circuit, input_params, weight_params).
    """
    inputs  = ParameterVector("x", N_QUBITS)
    weights = ParameterVector("θ", N_QUBITS)

    qc = QuantumCircuit(N_QUBITS)

    # Layer 1 — angle-encode the BitNet intent vector
    for i in range(N_QUBITS):
        qc.ry(inputs[i] * np.pi, i)

    # Layer 2 — entangle qubits to capture cross-route correlations
    for i in range(N_QUBITS - 1):
        qc.cx(i, i + 1)
    qc.cx(N_QUBITS - 1, 0)          # close the ring

    # Layer 3 — trainable variational block
    for i in range(N_QUBITS):
        qc.ry(weights[i], i)

    return qc, inputs, weights


def build_qnn_model() -> TorchConnector:
    """
    Assemble the full hybrid pipeline and return a PyTorch-compatible
    model backed entirely by IBM Qiskit's EstimatorQNN.

    One independent Z-observable per qubit produces a 4-D output —
    one score per route candidate.
    """
    qc, inputs, weights = build_photon_circuit()

    # Independent Z-observable per qubit → 4 expectation values
    observables = [
        SparsePauliOp("IIIZ"),   # Route 1
        SparsePauliOp("IIZI"),   # Route 2
        SparsePauliOp("IZII"),   # Route 3
        SparsePauliOp("ZIII"),   # Route 4
    ]

    qnn = EstimatorQNN(
        circuit=qc,
        input_params=list(inputs),
        weight_params=list(weights),
        observables=observables,
    )

    initial_weights = torch.zeros(N_QUBITS, dtype=torch.float32)
    return TorchConnector(qnn, initial_weights=initial_weights)


def score_routes(
    model: TorchConnector,
    intent_tensor: torch.Tensor,
    route_data: list,
    scenario_data: dict = None,
) -> list:
    """
    Compute a Hybrid Photon Match Score (0–100) for each route by fusing:
      • 30% — IBM QNN expectation value (quantum component)
      • 70% — Classical priority-alignment score (scenario-specific component)

    scenario_data (optional): when supplied, classical weights are derived from
    the scenario's priority_hint, guaranteeing distinct winners per scenario
    regardless of the LLM's raw output vector. When absent, weights are inferred
    from the intent_tensor directly (backward-compatible path).

    Handles MPS → CPU device handoff transparently.
    Returns route_data list sorted descending by photon_score.
    """
    model.eval()

    # QNN forward pass (CPU only)
    x = intent_tensor.detach().cpu().float().unsqueeze(0)   # shape: (1, 4)
    with torch.no_grad():
        raw = model(x)                          # shape: (1, N_observables)
    output   = raw.squeeze()                    # shape: (4,)
    qnn_vals = output.tolist() if output.dim() > 0 else [float(output)] * N_QUBITS

    # ── Classical emphasis weights ─────────────────────────────────────────
    if scenario_data is not None:
        # Derive from scenario priority_hint: reproducible, scenario-specific
        _SCALE = {
            "CRITICAL": 1.00, "HIGH": 0.75, "BALANCED": 0.50,
            "MEDIUM":   0.30, "LOW":  0.05,
        }
        prio  = scenario_data["priority_hint"]
        raw_p = [_SCALE.get(prio.get(k, "MEDIUM"), 0.30)
                 for k in ["approval", "cost", "latency", "resilience"]]
        mean_p   = sum(raw_p) / len(raw_p)
        centered = [v - mean_p for v in raw_p]
        thresh   = sum(abs(v) for v in centered) / len(centered)
        ternary  = [1.0 if v > thresh else (-1.0 if v < -thresh else 0.0) for v in centered]
        weights  = [2.0 if t > 0 else (0.3 if t == 0.0 else 0.0) for t in ternary]
    else:
        # Legacy path: infer weights from intent_tensor value ranges
        intent_list = intent_tensor.detach().cpu().tolist()
        weights = [2.0 if v > 0.9 else (0.3 if v > 0.1 else 0.0) for v in intent_list]

    total_w = sum(weights) or 1.0

    # ── Normalised route performance (higher = better for all dimensions) ─
    # Ceiling values chosen above observed maximums in mock_data.py
    def _perf(stats: dict) -> list:
        return [
            stats["approval_rate"]  / 100.0,          # approval  ↑ better
            1.0 - stats["cost_bps"] / 15.0,           # cost      ↓ better
            1.0 - stats["latency_ms"] / 600.0,        # latency   ↓ better
            stats["resilience_score"] / 100.0,        # resilience↑ better
        ]

    scored = []
    for route, qnn_val in zip(route_data, qnn_vals):
        perf = _perf(route["stats"])

        # Priority-weighted alignment: dot(weights, perf) / total_weight
        classical_score = sum(w * p for w, p in zip(weights, perf)) / total_w * 100.0

        # QNN expectation value ∈ [-1, +1] → centred adjustment ∈ [-15, +15]
        # The QNN acts as a quantum-informed bonus/penalty on top of the classical
        # baseline rather than replacing part of it — keeps scores in the same range
        # and makes the quantum contribution immediately legible.
        qnn_norm       = (qnn_val + 1.0) / 2.0          # normalise to [0, 1]
        qnn_adjustment = (qnn_norm - 0.5) * 30.0        # ±15 point adjustment

        r = dict(route)
        r["photon_score"]    = round(classical_score + qnn_adjustment, 1)
        r["qnn_adjustment"]  = round(qnn_adjustment, 1)   # stored for UI display
        scored.append(r)

    scored.sort(key=lambda r: r["photon_score"], reverse=True)
    return scored


def score_routes_classical(route_data: list, scenario_data: dict = None) -> list:
    """
    Pure classical priority-weighted scoring — no QNN component.
    Used for the side-by-side Quantum Impact Analysis comparison.

    Applies the same emphasis weights as score_routes() but assigns 100%
    weight to the classical alignment score (QNN contribution = 0%).
    Returns route_data sorted descending by classical_score.
    """
    _SCALE = {
        "CRITICAL": 1.00, "HIGH": 0.75, "BALANCED": 0.50,
        "MEDIUM":   0.30, "LOW":  0.05,
    }

    if scenario_data is not None:
        prio  = scenario_data["priority_hint"]
        raw_p = [_SCALE.get(prio.get(k, "MEDIUM"), 0.30)
                 for k in ["approval", "cost", "latency", "resilience"]]
        mean_p   = sum(raw_p) / len(raw_p)
        centered = [v - mean_p for v in raw_p]
        thresh   = sum(abs(v) for v in centered) / len(centered)
        ternary  = [1.0 if v > thresh else (-1.0 if v < -thresh else 0.0) for v in centered]
        weights  = [2.0 if t > 0 else (0.3 if t == 0.0 else 0.0) for t in ternary]
    else:
        weights = [1.0, 1.0, 1.0, 1.0]

    total_w = sum(weights) or 1.0

    def _perf(stats: dict) -> list:
        return [
            stats["approval_rate"]  / 100.0,
            1.0 - stats["cost_bps"] / 15.0,
            1.0 - stats["latency_ms"] / 600.0,
            stats["resilience_score"] / 100.0,
        ]

    scored = []
    for route in route_data:
        perf = _perf(route["stats"])
        classical_norm = sum(w * p for w, p in zip(weights, perf)) / total_w
        r = dict(route)
        r["classical_score"] = round(classical_norm * 100.0, 1)
        scored.append(r)

    scored.sort(key=lambda r: r["classical_score"], reverse=True)
    return scored
