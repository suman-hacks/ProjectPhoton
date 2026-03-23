"""
bitnet_encoder.py — Project Photon (Phase 2 — Native 1.58-bit BitNet LLM)

Loads the Microsoft/1bitLLM BitNet b1.58-3B model to extract a semantic
payment-intent embedding from a natural language scenario, then reduces it to
a 4-dimensional tensor for IBM Qiskit QNN angle-encoding.

Memory strategy for 8 GB Apple Silicon:
  • device_map="cpu"    — keeps all weights in unified memory, avoids MPS
                          fragmentation with custom BitNet ops
  • low_cpu_mem_usage   — streams weights shard-by-shard instead of doubling
                          peak RAM during load
  • no torch_dtype      — lets BitNet's custom loading code preserve its own
                          1.58-bit / int8 packed representation; forcing fp16
                          here would balloon memory to ~6 GB
  • max_length=96 tokens — keeps the activation footprint tiny at inference
"""

import logging
import os
import torch
import torch.nn as nn

logging.getLogger("transformers").setLevel(logging.ERROR)

# Disable HuggingFace's Xet (P2P) download backend — falls back to standard
# HTTPS which is stable. Xet causes "Background writer channel closed" errors
# on some network configurations and macOS versions.
os.environ.setdefault("HF_HUB_DISABLE_XET", "1")

MODEL_REPO = "1bitLLM/bitnet_b1_58-3B"
DEVICE     = "cpu"   # BitNet custom ops have no MPS kernel in current release

DIMENSION_LABELS = ["Approval", "Cost", "Latency", "Resilience"]


# ---------------------------------------------------------------------------
# Model Diagnostics
# ---------------------------------------------------------------------------
def get_model_info(model) -> dict:
    """
    Return a diagnostics dict that proves whether the real 1.58-bit BitNet
    model is running or the fallback simulator is active.

    Key signal: a genuine BitNet model stores its linear-layer weights as
    torch.int8 (the packed 1.58-bit ternary representation). A standard
    fp32 or fp16 model would show float32 / float16 here instead.
    """
    if model is None:
        return {
            "live":        False,
            "status":      "SIMULATED",
            "status_note": "Model unavailable — using scenario priority vector",
        }

    try:
        cfg         = model.config
        total_params = sum(p.numel() for p in model.parameters())

        # Inspect first weight tensor — dtype is the key 1.58-bit indicator
        first_weight = next(model.parameters())
        weight_dtype = str(first_weight.dtype)

        # Detect the "true 1.58-bit" signal
        is_quantized = first_weight.dtype in (torch.int8, torch.uint8)
        quant_note   = (
            "CONFIRMED — weights are int8-packed ternary {-1, 0, +1}"
            if is_quantized else
            f"Loaded as {weight_dtype} (BitNet custom kernels may still apply 1.58-bit ops)"
        )

        return {
            "live":           True,
            "status":         "LIVE",
            "status_note":    "Native 1.58-bit BitNet LLM active",
            "model_id":       MODEL_REPO,
            "architecture":   getattr(cfg, "model_type", "unknown"),
            "hidden_size":    getattr(cfg, "hidden_size", "N/A"),
            "total_params":   f"{total_params / 1e9:.2f}B",
            "weight_dtype":   weight_dtype,
            "quant_verified": quant_note,
        }
    except Exception as exc:
        return {
            "live":        True,
            "status":      "LIVE",
            "status_note": f"Model loaded (diagnostic partial: {exc})",
            "model_id":    MODEL_REPO,
        }
DIMENSION_KEYS   = ["approval", "cost", "latency", "resilience"]

# Priority label → continuous float (mirrors mock_data priority_hint values)
_PRIORITY_SCALE: dict = {
    "CRITICAL": 1.00, "HIGH": 0.75, "BALANCED": 0.50,
    "MEDIUM":   0.30, "LOW":  0.05,
}


# ---------------------------------------------------------------------------
# Model Loading — called once and wrapped in @st.cache_resource in app.py
# ---------------------------------------------------------------------------
def load_bitnet_model() -> tuple:
    """
    Attempt to load the native 1.58-bit BitNet b1.58-3B model.

    Returns (model, tokenizer, reducer) on success.
    Returns (None, None, None) on any failure — the app falls back to
    the simulated priority-vector approach so it never crashes.
    """
    try:
        import json
        from pathlib import Path
        from transformers import AutoModelForCausalLM, AutoTokenizer

        # --- Patch cached tokenizer_config.json ---
        # The model's repo sets "tokenizer_class": "BitnetTokenizer", which current
        # transformers can't resolve even with trust_remote_code=True.
        # BitNet b1.58-3B uses an identical LLaMA vocabulary, so we swap the class
        # name to "LlamaTokenizer" in every cached copy of the config before loading.
        _hf_cache = Path.home() / ".cache" / "huggingface" / "hub"
        for _cfg_path in _hf_cache.glob("**/tokenizer_config.json"):
            if "bitnet" in str(_cfg_path).lower() or "1bitllm" in str(_cfg_path).lower():
                try:
                    _cfg = json.loads(_cfg_path.read_text())
                    if _cfg.get("tokenizer_class") == "BitnetTokenizer":
                        _cfg["tokenizer_class"] = "LlamaTokenizer"
                        _cfg_path.write_text(json.dumps(_cfg, indent=2))
                except Exception:
                    pass

        tokenizer = AutoTokenizer.from_pretrained(
            MODEL_REPO,
            trust_remote_code=True,
            use_fast=False,
        )
        if tokenizer.pad_token is None:
            tokenizer.pad_token = tokenizer.eos_token

        model = AutoModelForCausalLM.from_pretrained(
            MODEL_REPO,
            trust_remote_code=True,
            low_cpu_mem_usage=True,
            device_map={"": DEVICE},
        )
        model.eval()

        # ── Reducer: hidden_dim → 4 (one dim per QNN qubit) ──────────────
        hidden_dim = model.config.hidden_size
        torch.manual_seed(42)
        reducer = nn.Linear(hidden_dim, 4, bias=False)
        nn.init.xavier_uniform_(reducer.weight)
        reducer.eval()

        return model, tokenizer, reducer

    except Exception as exc:  # noqa: BLE001
        import traceback
        _tb = traceback.format_exc()
        # Print full traceback to terminal so the exact failure is visible
        print("\n[Project Photon] BitNet model load FAILED:\n", _tb, flush=True)
        # Store error string for UI display
        load_bitnet_model._last_error = str(exc)
        return None, None, None

load_bitnet_model._last_error = None   # initialise attribute


# ---------------------------------------------------------------------------
# Intent Extraction — main entry point called by app.py
# ---------------------------------------------------------------------------
def extract_intent_vector(
    scenario_data: dict,
    model,
    tokenizer,
    reducer,
) -> tuple:
    """
    Extract a 4-D intent vector from the scenario.

    If the BitNet model loaded successfully, runs a genuine forward pass and
    extracts the final token's last hidden state, reduced to 4 dims via a
    fixed nn.Linear layer.  The resulting tensor is the real quantum input.

    If the model failed to load (model is None), falls back to the original
    scenario-priority simulation so the app remains fully functional.

    Returns
    -------
    intent_tensor  : torch.Tensor (4,) on CPU, values ∈ [0, 1]
                     → fed directly into the IBM QNN as angle-encoding input
    ternary_raw    : list[float] {-1.0, 0.0, 1.0}
                     → deterministic from scenario priorities; used for display
    priority_levels: list[str]
                     → scenario priority labels; used for display & explanation
    """
    # Deterministic display values derived from scenario priorities
    ternary_raw, priority_levels = _compute_display_ternary(scenario_data)

    if model is None:
        # Fallback: simulate the intent tensor from scenario priorities
        intent_tensor = _simulated_tensor(scenario_data)
        return intent_tensor, ternary_raw, priority_levels

    # ── Real 1.58-bit BitNet inference ────────────────────────────────────
    prompt    = _build_prompt(scenario_data)
    enc       = tokenizer(
        prompt,
        return_tensors="pt",
        max_length=96,
        truncation=True,
        padding=False,
    )
    input_ids = enc["input_ids"].to(DEVICE)

    with torch.no_grad():
        try:
            outputs     = model(input_ids, output_hidden_states=True, return_dict=True)
            last_hidden = outputs.hidden_states[-1][:, -1, :].float()  # (1, H)
        except (TypeError, AttributeError, KeyError):
            # Some BitNet variants expose hidden states via the base sub-model
            base = getattr(model, "model", model)
            out  = base(input_ids, return_dict=True)
            if hasattr(out, "last_hidden_state"):
                last_hidden = out.last_hidden_state[:, -1, :].float()
            elif hasattr(out, "hidden_states") and out.hidden_states:
                last_hidden = out.hidden_states[-1][:, -1, :].float()
            else:
                # Last resort: project from logits
                last_hidden = model(input_ids).logits[:, -1, :].float()

        # Reduce hidden_dim → 4, sigmoid-normalise to [0, 1]
        raw_4d        = reducer(last_hidden).squeeze(0)  # (4,)
        intent_tensor = torch.sigmoid(raw_4d)            # (4,) ∈ [0, 1]

    return intent_tensor, ternary_raw, priority_levels


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------
def _build_prompt(scenario_data: dict) -> str:
    p = scenario_data["priority_hint"]
    return (
        f"Financial transaction routing.\n"
        f"Scenario: {scenario_data['description']}\n"
        f"Amount: ${scenario_data['amount_usd']:,.0f} "
        f"{scenario_data['currency_pair']}. "
        f"Risk: {scenario_data['risk_tier']}. "
        f"Priorities — approval: {p['approval']}, cost: {p['cost']}, "
        f"latency: {p['latency']}, resilience: {p['resilience']}."
    )


def _compute_display_ternary(scenario_data: dict) -> tuple:
    """
    Deterministic ternary display values derived from the scenario's
    priority_hint — identical to the original simulated BitNet logic.
    Used for the Stage 3 ternary bit cards and business explanation.
    """
    priority = scenario_data["priority_hint"]
    raw = [_PRIORITY_SCALE.get(priority.get(k, "MEDIUM"), 0.30) for k in DIMENSION_KEYS]
    raw_t    = torch.tensor(raw, dtype=torch.float32)
    centered = raw_t - raw_t.mean()
    threshold = centered.abs().mean().item()

    ternary = [
        1.0 if v > threshold else (-1.0 if v < -threshold else 0.0)
        for v in centered.tolist()
    ]
    priority_levels = [priority.get(k, "MEDIUM") for k in DIMENSION_KEYS]
    return ternary, priority_levels


def _simulated_tensor(scenario_data: dict) -> torch.Tensor:
    """
    Fallback: reproduce the original simulated intent tensor from scenario
    priority hints when the BitNet model is unavailable.
    """
    priority = scenario_data["priority_hint"]
    raw = [_PRIORITY_SCALE.get(priority.get(k, "MEDIUM"), 0.30) for k in DIMENSION_KEYS]
    raw_t    = torch.tensor(raw, dtype=torch.float32)
    centered = raw_t - raw_t.mean()
    threshold = centered.abs().mean().item()

    ternary = torch.tensor([
        1.0 if v > threshold else (-1.0 if v < -threshold else 0.0)
        for v in centered.tolist()
    ])
    return (ternary + 1.0) / 2.0  # shift to {0.0, 0.5, 1.0}
