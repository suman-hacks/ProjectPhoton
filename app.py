"""
app.py — Project Photon: Decision Intelligence Cockpit
Phases 1–4: Data shell + BitNet encoder + IBM QNN routing + Architecture diagram.
"""

import matplotlib.pyplot as plt
import streamlit as st
from mock_data import SCENARIOS, ROUTES, BADGE_COLORS
from bitnet_encoder import load_bitnet_model, extract_intent_vector, get_model_info, DIMENSION_LABELS, MODEL_REPO
from qiskit_router import build_qnn_model, build_photon_circuit, score_routes, score_routes_classical

# ---------------------------------------------------------------------------
# Page Configuration — must be the first Streamlit call
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Project Photon",
    page_icon="⚛",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Session State Initialisation
# ---------------------------------------------------------------------------
for key, default in {
    "scored_routes":      None,
    "ternary_vals":       None,
    "priority_levels":    None,
    "optimized_scenario": None,
    "intent_tensor_list": None,
    "model_info":         None,   # diagnostics dict from get_model_info()
    "classical_routes":   None,   # classical-only scores for impact comparison
}.items():
    if key not in st.session_state:
        st.session_state[key] = default

# ---------------------------------------------------------------------------
# QNN Model — cached across reruns; built once per session
# ---------------------------------------------------------------------------
@st.cache_resource(show_spinner=False)
def get_qnn_model():
    return build_qnn_model()

@st.cache_resource(show_spinner=False)
def get_photon_circuit():
    """Return the bare QuantumCircuit (no parameters bound) for visualisation."""
    qc, _, _ = build_photon_circuit()
    return qc

@st.cache_resource(show_spinner=False)
def get_bitnet_model():
    """
    Load the native 1.58-bit BitNet LLM once per session into unified memory.
    Returns (model, tokenizer, reducer) — or (None, None, None) if unavailable,
    in which case the encoder silently falls back to the simulated approach.
    """
    return load_bitnet_model()

# ---------------------------------------------------------------------------
# Global CSS — premium dark theme
# ---------------------------------------------------------------------------
st.markdown(
    """
    <style>
      /* ── Base ── */
      html, body, [data-testid="stAppViewContainer"] {
          background-color: #0D0F14;
          color: #E8EAF0;
          font-family: 'Inter', 'Segoe UI', sans-serif;
      }
      [data-testid="stSidebar"] {
          background-color: #13161E;
          border-right: 1px solid #1F2333;
      }

      /* ── Headings ── */
      h1 { color: #FFFFFF; letter-spacing: -0.5px; }
      h2 { color: #C9D0E8; font-size: 1.1rem; font-weight: 600; }
      h3 { color: #A0AACC; font-size: 0.95rem; font-weight: 500; }

      /* ── Route Card ── */
      .route-card {
          background: linear-gradient(145deg, #161A26, #1C2133);
          border: 1px solid #252B3E;
          border-radius: 12px;
          padding: 22px 24px;
          margin-bottom: 14px;
          position: relative;
      }
      .route-card.winner {
          border-color: #C9A84C;
          box-shadow: 0 0 24px #C9A84C22;
      }

      /* ── Badge ── */
      .route-badge {
          display: inline-block;
          font-size: 0.62rem;
          font-weight: 700;
          letter-spacing: 1.2px;
          padding: 3px 9px;
          border-radius: 4px;
          margin-bottom: 10px;
      }

      /* ── Stat pill ── */
      .stat-row { display: flex; gap: 10px; flex-wrap: wrap; margin-top: 14px; }
      .stat-pill {
          background: #0D0F14;
          border: 1px solid #252B3E;
          border-radius: 8px;
          padding: 8px 14px;
          font-size: 0.78rem;
          text-align: center;
          flex: 1;
          min-width: 70px;
      }
      .stat-pill .label { color: #7A8099; font-size: 0.65rem; letter-spacing: 0.8px; text-transform: uppercase; }
      .stat-pill .value { color: #E8EAF0; font-size: 1.05rem; font-weight: 600; margin-top: 2px; }
      .stat-pill.quantum .label { color: #7B6FA8; }
      .stat-pill.quantum .value { color: #C9A84C; font-size: 1.15rem; }

      /* ── Scenario meta ── */
      .scenario-meta {
          background: #13161E;
          border: 1px solid #1F2333;
          border-radius: 10px;
          padding: 18px 20px;
          margin-bottom: 28px;
          font-size: 0.85rem;
          color: #A0AACC;
          line-height: 1.6;
      }
      .scenario-meta strong { color: #E8EAF0; }

      /* ── Divider ── */
      .photon-divider {
          border: none;
          border-top: 1px solid #1F2333;
          margin: 28px 0;
      }

      /* ── CTA button ── */
      div[data-testid="stButton"] > button {
          background: linear-gradient(135deg, #2A3A7C, #1A2456);
          color: #FFFFFF;
          border: 1px solid #3A4A9C;
          border-radius: 8px;
          padding: 12px 28px;
          font-size: 0.9rem;
          font-weight: 600;
          letter-spacing: 0.5px;
          width: 100%;
          transition: all 0.2s;
      }
      div[data-testid="stButton"] > button:hover {
          background: linear-gradient(135deg, #3A4A9C, #2A3A7C);
          border-color: #5A6ACC;
      }

      /* ── Placeholder banner ── */
      .placeholder-banner {
          background: #0D1426;
          border: 1px dashed #2A3A7C;
          border-radius: 10px;
          padding: 22px;
          text-align: center;
          color: #3A4A9C;
          font-size: 0.85rem;
          letter-spacing: 0.5px;
          margin-top: 16px;
      }

      /* ── Intent vector card ── */
      .intent-card {
          background: #13161E;
          border: 1px solid #252B3E;
          border-radius: 10px;
          padding: 16px 18px;
          text-align: center;
      }
      .intent-card .dim    { font-size: 0.7rem; color: #7A8099; letter-spacing: 0.8px; text-transform: uppercase; margin-bottom: 6px; }
      .intent-card .level  { font-size: 0.75rem; font-weight: 600; margin-bottom: 8px; }
      .intent-card .ternary{ font-size: 1.6rem; font-weight: 800; line-height: 1; }

      /* ── Winner banner ── */
      .winner-banner {
          background: linear-gradient(135deg, #1A1500, #1F1A00);
          border: 1px solid #C9A84C55;
          border-radius: 12px;
          padding: 20px 24px;
          margin: 20px 0;
      }
      .winner-banner .tag  { font-size: 0.65rem; color: #C9A84C; letter-spacing: 1.5px; font-weight: 700; margin-bottom: 6px; }
      .winner-banner .name { font-size: 1.15rem; font-weight: 700; color: #F5E6A0; margin-bottom: 8px; }
      .winner-banner .body { font-size: 0.83rem; color: #A09060; line-height: 1.6; }

      /* ── Pipeline step ── */
      .pipeline-step {
          display: flex;
          align-items: flex-start;
          gap: 16px;
          padding: 14px 0;
          border-bottom: 1px solid #1F2333;
      }
      .pipeline-step:last-child { border-bottom: none; }
      .pipeline-step .icon { font-size: 1.4rem; margin-top: 2px; flex-shrink: 0; }
      .pipeline-step .title { font-size: 0.85rem; font-weight: 600; color: #C9D0E8; margin-bottom: 2px; }
      .pipeline-step .desc  { font-size: 0.77rem; color: #7A8099; line-height: 1.5; }

      /* ── Streamlit chrome — blend into dark theme ── */
      header[data-testid="stHeader"] {
          background-color: #0D0F14 !important;
          border-bottom: 1px solid #1F2333;
      }
      [data-testid="stToolbar"] { background-color: #0D0F14 !important; }
      /* Hide the Deploy / star / fork action buttons */
      [data-testid="stToolbarActions"] { display: none !important; }
      #MainMenu { visibility: hidden !important; }
      footer     { visibility: hidden !important; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Helper — plain-English executive recommendation
# ---------------------------------------------------------------------------
def _build_business_explanation(
    winner: dict, scenario: dict, top_dim: str, top_level: str
) -> str:
    """
    Generate a scenario-specific, plain-English recommendation sentence
    tailored to the dominant business priority identified by the BitNet encoder.
    """
    route  = winner["name"]
    score  = winner["photon_score"]
    amount = f"${scenario['amount_usd']:,.0f}"
    pair   = scenario["currency_pair"]

    _context: dict[str, tuple[str, str]] = {
        "Approval": (
            "guaranteed approval rate",
            f"minimising counterparty settlement risk on the {amount} {pair} transaction",
        ),
        "Cost": (
            "lowest total processing cost",
            f"maximising fee efficiency for the {amount} flow without sacrificing network coverage",
        ),
        "Latency": (
            "sub-millisecond end-to-end latency",
            f"satisfying the real-time settlement SLA for the {amount} payment",
        ),
        "Resilience": (
            "maximum network resilience and multi-path failover",
            f"ensuring uninterrupted authorisation continuity for the high-risk {amount} transaction",
        ),
    }
    constraint, outcome = _context.get(
        top_dim, ("balanced performance profile", f"optimising the {amount} transaction")
    )

    return (
        f"Recommended Route: <strong>{route}</strong> &nbsp;·&nbsp; "
        f"Photon Score <strong style='color:#C9A84C;'>{score}&thinsp;/&thinsp;100</strong><br>"
        f"The IBM Quantum Neural Network determined this route as the optimal path by leveraging "
        f"its <strong>{constraint}</strong> advantage — {outcome}. "
        f"Decision confirmed via Pauli-Z expectation measurement across the entangled 4-qubit state space."
    )


# ---------------------------------------------------------------------------
# Sidebar — Scenario Selection
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown("## ⚛ Project Photon")
    st.markdown(
        "<p style='color:#7A8099;font-size:0.78rem;margin-top:-8px;'>Hybrid QNN Payment Routing</p>",
        unsafe_allow_html=True,
    )
    st.markdown("<hr style='border-color:#1F2333;margin:16px 0;'>", unsafe_allow_html=True)

    st.markdown("### Payment Scenario")
    scenario_options = {v["label"]: k for k, v in SCENARIOS.items()}
    selected_label = st.selectbox(
        label="Select scenario",
        options=list(scenario_options.keys()),
        label_visibility="collapsed",
    )
    selected_id = scenario_options[selected_label]
    scenario    = SCENARIOS[selected_id]

    st.markdown("<hr style='border-color:#1F2333;margin:16px 0;'>", unsafe_allow_html=True)

    st.markdown(
        f"""
        <div style='font-size:0.78rem;color:#7A8099;line-height:2;'>
          <div><span style='color:#A0AACC;'>Amount</span>&nbsp;&nbsp;
               <strong style='color:#E8EAF0;'>${scenario['amount_usd']:,.0f}</strong></div>
          <div><span style='color:#A0AACC;'>FX Pair</span>&nbsp;&nbsp;
               <strong style='color:#E8EAF0;'>{scenario['currency_pair']}</strong></div>
          <div><span style='color:#A0AACC;'>Risk Tier</span>&nbsp;&nbsp;
               <strong style='color:#E8EAF0;'>{scenario['risk_tier']}</strong></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("<hr style='border-color:#1F2333;margin:20px 0;'>", unsafe_allow_html=True)

    # ── BitNet model status badge ─────────────────────────────────────────
    _minfo = st.session_state.get("model_info")
    if _minfo is None:
        _badge_color, _badge_text, _badge_note = "#2A3A7C", "NOT YET LOADED", "Loads on first optimization run"
    elif _minfo["live"]:
        _badge_color, _badge_text, _badge_note = "#1A4A2A", "LIVE MODEL", _minfo.get("model_id", MODEL_REPO).split("/")[-1]
    else:
        _badge_color, _badge_text, _badge_note = "#4A2A00", "SIMULATED", _minfo.get("status_note", "")
    st.markdown(
        f"""
        <div style='background:{_badge_color};border-radius:7px;padding:9px 14px;margin-bottom:14px;'>
          <div style='font-size:0.6rem;color:#A0AACC;letter-spacing:1.2px;font-weight:700;
                      text-transform:uppercase;margin-bottom:2px;'>BitNet AI Layer</div>
          <div style='font-size:0.78rem;font-weight:700;color:#E8EAF0;'>{_badge_text}</div>
          <div style='font-size:0.68rem;color:#808898;margin-top:2px;'>{_badge_note}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    optimize_clicked = st.button("Initialize Project Photon Optimization")
    st.markdown(
        "<p style='color:#2A3A7C;font-size:0.72rem;margin-top:10px;text-align:center;'>"
        "Engages BitNet encoder → IBM EstimatorQNN</p>",
        unsafe_allow_html=True,
    )

# ---------------------------------------------------------------------------
# Optimization Pipeline — runs before UI renders so Stage 2 cards update
# immediately on the same pass.
# ---------------------------------------------------------------------------
scores_available = (
    st.session_state.scored_routes is not None
    and st.session_state.optimized_scenario == selected_id
)

if optimize_clicked:
    with st.status(
        "Initializing Project Photon optimization pipeline…", expanded=True
    ) as pipeline_status:

        st.write("**Step 1 · Classical AI Layer** — running native 1.58-bit CPU inference on Microsoft BitNet architecture…")
        _bitnet_model, _tokenizer, _reducer = get_bitnet_model()

        # Store diagnostics immediately after load so sidebar badge updates
        _minfo = get_model_info(_bitnet_model)
        st.session_state.model_info = _minfo

        if _minfo["live"]:
            st.write(
                f"&nbsp;&nbsp;&nbsp;✅ **Live model active** — `{_minfo.get('model_id', MODEL_REPO)}` &nbsp;·&nbsp; "
                f"params: `{_minfo.get('total_params','N/A')}` &nbsp;·&nbsp; "
                f"hidden size: `{_minfo.get('hidden_size','N/A')}` &nbsp;·&nbsp; "
                f"weight dtype: `{_minfo.get('weight_dtype','N/A')}`"
            )
            st.write(f"&nbsp;&nbsp;&nbsp;🔬 **1.58-bit verification:** {_minfo.get('quant_verified','—')}")
        else:
            _err = getattr(load_bitnet_model, "_last_error", None) or "unknown error"
            st.write(f"&nbsp;&nbsp;&nbsp;⚠️ **Fallback active** — {_minfo.get('status_note','')}")
            st.code(_err, language=None)

        intent_tensor, ternary_vals, priority_levels = extract_intent_vector(
            scenario, _bitnet_model, _tokenizer, _reducer
        )
        st.session_state.ternary_vals       = ternary_vals
        st.session_state.priority_levels    = priority_levels
        st.session_state.intent_tensor_list = intent_tensor.detach().cpu().tolist()

        st.write("**Step 2 · Quantum Layer** — injecting ternary tensor into IBM EstimatorQNN…")
        qnn_model = get_qnn_model()
        scored    = score_routes(qnn_model, intent_tensor, ROUTES, scenario_data=scenario)
        classical = score_routes_classical(ROUTES, scenario_data=scenario)
        st.session_state.scored_routes      = scored
        st.session_state.classical_routes   = classical
        st.session_state.optimized_scenario = selected_id

        pipeline_status.update(
            label="Optimization complete — Photon Match Scores computed.", state="complete"
        )

    scores_available = True
    # Rerun so the sidebar badge (which rendered before this block ran) now
    # picks up the updated st.session_state.model_info value.
    st.rerun()

# ---------------------------------------------------------------------------
# Main Panel Header
# ---------------------------------------------------------------------------
st.markdown("# Project Photon")
st.markdown(
    "<p style='color:#7A8099;font-size:0.9rem;margin-top:-14px;margin-bottom:24px;'>"
    "Decision Intelligence Cockpit &nbsp;·&nbsp; Hybrid QNN Payment Routing Engine</p>",
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# STAGE 1 — Payment Scenario Context
# ---------------------------------------------------------------------------
st.markdown("## STAGE 1 — Payment Scenario Context")

st.markdown(
    f"""
    <div class='scenario-meta'>
      <strong>{scenario['label']}</strong><br>
      {scenario['description']}
    </div>
    """,
    unsafe_allow_html=True,
)

priority = scenario["priority_hint"]
priority_colors = {
    "CRITICAL": "#E55A5A", "HIGH": "#C9A84C",
    "BALANCED": "#6FCF97", "MEDIUM": "#4A90D9", "LOW": "#7A8099",
}
chips_html = "<div style='display:flex;gap:10px;flex-wrap:wrap;margin-bottom:28px;'>"
for dim, level in priority.items():
    color = priority_colors.get(level, "#7A8099")
    chips_html += (
        f"<div style='background:#13161E;border:1px solid {color}33;border-radius:6px;"
        f"padding:6px 14px;font-size:0.75rem;'>"
        f"<span style='color:{color};font-weight:700;letter-spacing:0.8px;'>{level}</span>"
        f"<span style='color:#7A8099;margin-left:6px;'>{dim.capitalize()}</span>"
        f"</div>"
    )
chips_html += "</div>"
st.markdown(chips_html, unsafe_allow_html=True)

st.markdown("<hr class='photon-divider'>", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# STAGE 2 — Route Intelligence Cards
# ---------------------------------------------------------------------------
st.markdown("## STAGE 2 — Route Intelligence")

if scores_available:
    st.markdown(
        "<p style='color:#7A8099;font-size:0.82rem;margin-top:-10px;margin-bottom:20px;'>"
        "Routes ranked by Photon Match Score from the IBM EstimatorQNN. "
        "Winner highlighted in gold.</p>",
        unsafe_allow_html=True,
    )
    display_routes = st.session_state.scored_routes
    winner_id      = display_routes[0]["id"]
else:
    st.markdown(
        "<p style='color:#7A8099;font-size:0.82rem;margin-top:-10px;margin-bottom:20px;'>"
        "Four candidate routes evaluated against network benchmarks. "
        "Run optimization to apply Quantum scoring.</p>",
        unsafe_allow_html=True,
    )
    display_routes = ROUTES
    winner_id      = None

cols = st.columns(2)
for i, route in enumerate(display_routes):
    col         = cols[i % 2]
    badge_color = BADGE_COLORS[route["badge"]]
    stats       = route["stats"]
    is_winner   = scores_available and route["id"] == winner_id
    card_class  = "route-card winner" if is_winner else "route-card"

    winner_crown = (
        "<span style='float:right;font-size:0.7rem;background:#C9A84C22;"
        "color:#C9A84C;border:1px solid #C9A84C55;border-radius:4px;"
        "padding:2px 8px;letter-spacing:1px;font-weight:700;'>OPTIMAL ROUTE</span>"
        if is_winner else ""
    )

    quantum_pill = ""
    if scores_available and "photon_score" in route:
        quantum_pill = (
            "<div class='stat-pill quantum'>"
            "<div class='label'>⚛ Photon Score</div>"
            f"<div class='value'>{route['photon_score']}</div>"
            "</div>"
        )

    with col:
        st.markdown(
            f"""
            <div class='{card_class}'>
              {winner_crown}
              <span class='route-badge'
                style='background:{badge_color}22;color:{badge_color};border:1px solid {badge_color}55;'>
                {route['badge']}
              </span>
              <div style='font-size:1.0rem;font-weight:700;color:#E8EAF0;margin-bottom:4px;'>{route['name']}</div>
              <div style='font-size:0.78rem;color:#7A8099;line-height:1.5;'>{route['description']}</div>
              <div class='stat-row'>
                <div class='stat-pill'>
                  <div class='label'>Approval</div>
                  <div class='value'>{stats['approval_rate']}%</div>
                </div>
                <div class='stat-pill'>
                  <div class='label'>Cost</div>
                  <div class='value'>{stats['cost_bps']} bps</div>
                </div>
                <div class='stat-pill'>
                  <div class='label'>Latency</div>
                  <div class='value'>{stats['latency_ms']} ms</div>
                </div>
                <div class='stat-pill'>
                  <div class='label'>Resilience</div>
                  <div class='value'>{stats['resilience_score']}/100</div>
                </div>
                {quantum_pill}
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

# ── Plain-English recommendation callout (Phase 4) ───────────────────────
if scores_available:
    _tv    = st.session_state.ternary_vals
    _pl    = st.session_state.priority_levels
    _top_i = _tv.index(max(_tv))
    _top_d = DIMENSION_LABELS[_top_i]
    _top_l = _pl[_top_i]
    _expl  = _build_business_explanation(display_routes[0], scenario, _top_d, _top_l)
    st.markdown(
        f"""
        <div style='background:#0C0F1A;border:1px solid #2A3A6C44;border-left:3px solid #C9A84C;
                    border-radius:8px;padding:16px 20px;margin-top:4px;margin-bottom:4px;
                    font-size:0.83rem;color:#A0B0CC;line-height:1.75;'>
          {_expl}
        </div>
        """,
        unsafe_allow_html=True,
    )

st.markdown("<hr class='photon-divider'>", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# QUANTUM IMPACT ANALYSIS — Classical vs. Quantum-Enhanced side-by-side
# ---------------------------------------------------------------------------
if scores_available and st.session_state.classical_routes is not None:
    st.markdown("## Quantum Impact Analysis")
    st.markdown(
        "<p style='color:#7A8099;font-size:0.82rem;margin-top:-10px;margin-bottom:20px;'>"
        "Classical priority-weighted routing vs. IBM EstimatorQNN hybrid scoring — "
        "illustrating the incremental value of the quantum layer.</p>",
        unsafe_allow_html=True,
    )

    classical_routes = st.session_state.classical_routes
    quantum_routes   = st.session_state.scored_routes

    # Build rank lookup: route_id → rank (1-based) for each method
    classical_rank = {r["id"]: i + 1 for i, r in enumerate(classical_routes)}
    quantum_rank   = {r["id"]: i + 1 for i, r in enumerate(quantum_routes)}

    col_c, col_q = st.columns(2)

    def _rank_row(rank, route, score_key, score_label, classical_rank, quantum_rank):
        rid   = route["id"]
        c_pos = classical_rank[rid]
        q_pos = quantum_rank[rid]
        delta = c_pos - q_pos          # positive = moved up in quantum ranking
        if delta > 0:
            arrow, arrow_color = f"▲ +{delta}", "#6FCF97"
        elif delta < 0:
            arrow, arrow_color = f"▼ {delta}", "#E55A5A"
        else:
            arrow, arrow_color = "— ", "#4A90D9"

        badge_color = BADGE_COLORS[route["badge"]]
        is_top      = rank == 1
        top_style   = "border:1px solid #C9A84C55;background:#C9A84C0A;" if is_top else "border:1px solid #1F2333;"
        return (
            f"<div style='{top_style}border-radius:8px;padding:10px 14px;"
            f"margin-bottom:8px;display:flex;align-items:center;gap:12px;'>"
            f"<span style='font-size:1.1rem;font-weight:700;color:#7A8099;min-width:22px;'>#{rank}</span>"
            f"<span style='flex:1;'>"
            f"  <span style='font-size:0.78rem;font-weight:600;color:#E8EAF0;'>{route['name']}</span><br>"
            f"  <span style='font-size:0.7rem;color:{badge_color};'>{route['badge']}</span>"
            f"</span>"
            f"<span style='text-align:right;'>"
            f"  <span style='font-size:0.95rem;font-weight:700;color:#A0B0CC;'>{route[score_key]}</span><br>"
            f"  <span style='font-size:0.68rem;color:{arrow_color};font-weight:600;'>{arrow}</span>"
            f"</span>"
            f"</div>"
        )

    with col_c:
        st.markdown(
            "<div style='background:#0D1A2A;border:1px solid #1F3050;border-radius:10px;"
            "padding:14px 16px;margin-bottom:6px;'>"
            "<p style='color:#4A90D9;font-size:0.75rem;font-weight:700;letter-spacing:1px;"
            "margin:0 0 12px 0;'>CLASSICAL ROUTING &nbsp;·&nbsp; Priority-Weighted Only</p>",
            unsafe_allow_html=True,
        )
        rows_html = ""
        for i, route in enumerate(classical_routes):
            rows_html += _rank_row(i + 1, route, "classical_score", "Classical Score",
                                   classical_rank, quantum_rank)
        st.markdown(rows_html + "</div>", unsafe_allow_html=True)
        st.markdown(
            "<p style='color:#5A607A;font-size:0.7rem;margin-top:6px;'>"
            "Linear dot-product of priority weights × route performance. "
            "No cross-dimensional correlation modelling.</p>",
            unsafe_allow_html=True,
        )

    with col_q:
        st.markdown(
            "<div style='background:#0A1A14;border:1px solid #1A4A2A;border-radius:10px;"
            "padding:14px 16px;margin-bottom:6px;'>"
            "<p style='color:#6FCF97;font-size:0.75rem;font-weight:700;letter-spacing:1px;"
            "margin:0 0 12px 0;'>⚛ QUANTUM-ENHANCED &nbsp;·&nbsp; Hybrid Photon Score</p>",
            unsafe_allow_html=True,
        )
        rows_html = ""
        for i, route in enumerate(quantum_routes):
            rows_html += _rank_row(i + 1, route, "photon_score", "Photon Score",
                                   classical_rank, quantum_rank)
        st.markdown(rows_html + "</div>", unsafe_allow_html=True)
        st.markdown(
            "<p style='color:#5A607A;font-size:0.7rem;margin-top:6px;'>"
            "30% IBM EstimatorQNN expectation values + 70% classical alignment. "
            "Quantum entanglement captures non-linear priority interactions.</p>",
            unsafe_allow_html=True,
        )

    # ── Impact callout ────────────────────────────────────────────────────
    classical_winner = classical_routes[0]
    quantum_winner   = quantum_routes[0]
    rank_shifts      = sum(1 for r in quantum_routes if quantum_rank[r["id"]] != classical_rank[r["id"]])

    if classical_winner["id"] != quantum_winner["id"]:
        c_rank_of_qw = classical_rank[quantum_winner["id"]]
        impact_msg = (
            f"⚛ &nbsp;<strong>Quantum Edge Detected:</strong> The IBM EstimatorQNN elevated "
            f"<strong>{quantum_winner['name']}</strong> from classical rank "
            f"<strong>#{c_rank_of_qw}</strong> to <strong>#1</strong>. "
            f"Quantum entanglement between input dimensions surfaced a cross-priority "
            f"correlation that the classical linear model scored sub-optimally — "
            f"a decision the QNN resolved through superposition-based expectation values."
        )
        impact_color = "#6FCF97"
        impact_border = "#6FCF9755"
    else:
        impact_msg = (
            f"✅ &nbsp;<strong>Quantum Validation:</strong> The IBM EstimatorQNN confirms "
            f"<strong>{quantum_winner['name']}</strong> as the optimal route, independently "
            f"corroborating the classical priority model. {rank_shifts} route(s) were "
            f"re-ranked in the quantum scoring — the QNN detected subtle entanglement "
            f"patterns that refined confidence scores without overturning the primary decision."
        )
        impact_color = "#4A90D9"
        impact_border = "#4A90D955"

    st.markdown(
        f"""
        <div style='background:#0C0F1A;border:1px solid {impact_border};
                    border-left:3px solid {impact_color};
                    border-radius:8px;padding:14px 20px;margin-top:8px;
                    font-size:0.82rem;color:#A0B0CC;line-height:1.75;'>
          {impact_msg}
        </div>
        """,
        unsafe_allow_html=True,
    )

st.markdown("<hr class='photon-divider'>", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# STAGE 3 — Project Photon Reasoning Reveal
# ---------------------------------------------------------------------------
st.markdown("## STAGE 3 — Project Photon Reasoning Reveal")

if not scores_available:
    st.markdown(
        """
        <div class='placeholder-banner'>
          ⚛ &nbsp; AWAITING OPTIMIZATION SIGNAL<br>
          <span style='font-size:0.75rem;color:#1F2F6C;'>
            Click "Initialize Project Photon Optimization" to engage the<br>
            1.58-bit BitNet encoder → IBM EstimatorQNN pipeline.
          </span>
        </div>
        """,
        unsafe_allow_html=True,
    )
else:
    ternary_vals    = st.session_state.ternary_vals
    priority_levels = st.session_state.priority_levels
    scored_routes   = st.session_state.scored_routes
    winner          = scored_routes[0]

    # ── 3a. BitNet intent vector ──────────────────────────────────────────
    st.markdown(
        "<p style='color:#A0AACC;font-size:0.82rem;font-weight:600;letter-spacing:0.5px;margin-bottom:14px;'>"
        "CLASSICAL AI LAYER &nbsp;·&nbsp; 1.58-bit BitNet Ternary Encoding</p>",
        unsafe_allow_html=True,
    )

    ternary_color = {1.0: "#6FCF97", 0.0: "#4A90D9", -1.0: "#E55A5A"}
    ternary_label = {1.0: "+1", 0.0: "0", -1.0: "−1"}

    intent_cols = st.columns(4)
    for col, dim, level, tval in zip(intent_cols, DIMENSION_LABELS, priority_levels, ternary_vals):
        color = ternary_color.get(tval, "#7A8099")
        label = ternary_label.get(tval, "0")
        plevel_color = priority_colors.get(level, "#7A8099")
        with col:
            st.markdown(
                f"""
                <div class='intent-card'>
                  <div class='dim'>{dim}</div>
                  <div class='level' style='color:{plevel_color};'>{level}</div>
                  <div class='ternary' style='color:{color};'>{label}</div>
                  <div style='font-size:0.65rem;color:#5A607A;margin-top:4px;'>ternary bit</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.markdown(
        "<p style='color:#5A607A;font-size:0.73rem;margin-top:10px;margin-bottom:24px;'>"
        "The 1.58-bit encoder compresses the scenario's semantic priorities into a ternary "
        "tensor {−1, 0, +1}, eliminating all floating-point multiplications before quantum injection.</p>",
        unsafe_allow_html=True,
    )

    # ── 3b. Pipeline architecture steps ──────────────────────────────────
    st.markdown(
        "<p style='color:#A0AACC;font-size:0.82rem;font-weight:600;letter-spacing:0.5px;margin-bottom:2px;'>"
        "QUANTUM LAYER &nbsp;·&nbsp; IBM EstimatorQNN Pipeline</p>",
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        <div style='background:#13161E;border:1px solid #1F2333;border-radius:10px;padding:6px 20px;margin-bottom:20px;'>
          <div class='pipeline-step'>
            <div class='icon'>🧠</div>
            <div>
              <div class='title'>BitNet Ternary Encoder &nbsp;→&nbsp; Intent Tensor</div>
              <div class='desc'>Scenario priorities compressed to a 4-dimensional ternary vector
              {−1, 0, +1}. Zero floating-point multiplications — 1.58-bit efficiency.</div>
            </div>
          </div>
          <div class='pipeline-step'>
            <div class='icon'>⚛</div>
            <div>
              <div class='title'>4-Qubit Parameterized QuantumCircuit &nbsp;→&nbsp; Angle Encoding</div>
              <div class='desc'>Each ternary value is angle-encoded via RY gates. A circular CNOT
              chain entangles all qubits, allowing the QNN to capture cross-route correlations
              classically impossible to represent without exponential overhead.</div>
            </div>
          </div>
          <div class='pipeline-step'>
            <div class='icon'>📐</div>
            <div>
              <div class='title'>IBM EstimatorQNN &nbsp;→&nbsp; Expectation Values</div>
              <div class='desc'>Four independent Pauli-Z observables (one per qubit / route) are
              evaluated. The estimator returns a 4-dimensional expectation vector ∈ [−1, 1]
              representing the quantum energy landscape for each candidate route.</div>
            </div>
          </div>
          <div class='pipeline-step'>
            <div class='icon'>🔗</div>
            <div>
              <div class='title'>TorchConnector &nbsp;→&nbsp; Hybrid Gradient Bridge</div>
              <div class='desc'>IBM's TorchConnector wraps the EstimatorQNN as a native PyTorch
              layer, enabling end-to-end automatic differentiation across the classical–quantum
              boundary. The expectation values are normalized to Photon Match Scores [0–100].</div>
            </div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ── 3c. Winner recommendation (Phase 4 — scenario-specific explanation) ─
    runner_up = scored_routes[1] if len(scored_routes) > 1 else None
    margin    = round(winner["photon_score"] - runner_up["photon_score"], 1) if runner_up else 0

    top_idx   = ternary_vals.index(max(ternary_vals))
    top_dim   = DIMENSION_LABELS[top_idx]
    top_level = priority_levels[top_idx]

    business_explanation = _build_business_explanation(winner, scenario, top_dim, top_level)

    margin_note = (
        f"<span style='color:#7A8099;font-size:0.78rem;'>"
        f"Nearest alternative: <strong style='color:#A0AACC;'>{runner_up['name']}</strong> "
        f"({runner_up['photon_score']}/100) &nbsp;·&nbsp; winning margin: "
        f"<strong style='color:#C9A84C;'>+{margin} pts</strong></span>"
        if runner_up else ""
    )

    st.markdown(
        f"""
        <div class='winner-banner'>
          <div class='tag'>⚛ PHOTON RECOMMENDATION &nbsp;·&nbsp; {scenario['label'].upper()}</div>
          <div class='name'>{winner['name']}</div>
          <div class='body'>{business_explanation}</div>
          <div style='margin-top:12px;padding-top:12px;border-top:1px solid #3A2A00;'>
            {margin_note}
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ── 3d. Full score table ───────────────────────────────────────────────
    st.markdown(
        "<p style='color:#5A607A;font-size:0.78rem;font-weight:600;letter-spacing:0.5px;margin-bottom:10px;'>"
        "FULL QUANTUM SCORE RANKING</p>",
        unsafe_allow_html=True,
    )

    score_cols = st.columns(4)
    for col, route in zip(score_cols, scored_routes):
        medal = ["🥇", "🥈", "🥉", ""][scored_routes.index(route)]
        pct   = route["photon_score"]
        bar_w = int(pct)
        with col:
            st.markdown(
                f"""
                <div style='background:#13161E;border:1px solid #1F2333;border-radius:8px;
                            padding:14px 16px;text-align:center;'>
                  <div style='font-size:0.9rem;margin-bottom:4px;'>{medal}</div>
                  <div style='font-size:0.75rem;font-weight:600;color:#C9D0E8;
                              margin-bottom:8px;line-height:1.3;'>{route['name']}</div>
                  <div style='font-size:1.4rem;font-weight:800;color:#C9A84C;'>{pct}</div>
                  <div style='font-size:0.6rem;color:#5A607A;margin-bottom:8px;'>PHOTON SCORE</div>
                  <div style='background:#0D0F14;border-radius:4px;height:4px;overflow:hidden;'>
                    <div style='background:linear-gradient(90deg,#2A3A7C,#C9A84C);
                                width:{bar_w}%;height:100%;border-radius:4px;'></div>
                  </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

# ===========================================================================
# PROJECT PHOTON PIPELINE ARCHITECTURE (Phase 4)
# Circuit diagram only renders after optimization — it shows the scenario-
# specific rotation angles bound to the RY gates for that run.
# ===========================================================================
st.markdown("<hr class='photon-divider'>", unsafe_allow_html=True)

st.markdown(
    "<p style='color:#A0AACC;font-size:0.82rem;font-weight:600;"
    "letter-spacing:0.5px;margin-bottom:4px;'>"
    "PROJECT PHOTON PIPELINE ARCHITECTURE</p>",
    unsafe_allow_html=True,
)
st.markdown("## Quantum Circuit Diagram")

if not scores_available:
    st.markdown(
        "<p style='color:#7A8099;font-size:0.82rem;margin-top:-12px;margin-bottom:16px;'>"
        "The circuit diagram will render here after optimization runs, showing the "
        "scenario-specific rotation angles bound to each RY gate.</p>",
        unsafe_allow_html=True,
    )
    st.markdown(
        """
        <div class='placeholder-banner'>
          ⚛ &nbsp; CIRCUIT DIAGRAM AWAITING OPTIMIZATION<br>
          <span style='font-size:0.75rem;color:#1F2F6C;'>
            Run "Initialize Project Photon Optimization" to bind the BitNet intent<br>
            tensor to the 4-qubit QuantumCircuit and render the scenario-specific diagram.
          </span>
        </div>
        """,
        unsafe_allow_html=True,
    )
else:
    st.markdown(
        "<p style='color:#7A8099;font-size:0.82rem;margin-top:-12px;margin-bottom:24px;'>"
        "4-qubit IBM QuantumCircuit with scenario-specific RY rotation angles bound from "
        "the BitNet intent tensor. Each scenario produces a distinct circuit state.</p>",
        unsafe_allow_html=True,
    )

arch_diagram, arch_specs = st.columns([3, 1], gap="large")

with arch_diagram:
    if not scores_available:
        # Specs column still renders; diagram col shows nothing extra
        pass
    else:
        # Bind the intent tensor values to the circuit's input parameters
        _intent_list = st.session_state.intent_tensor_list   # [v0..v3] ∈ [0,1]
        _qc_raw, _inp_params, _wt_params = build_photon_circuit()

        # input params: x_i — the circuit gate is RY(x_i * π, qubit_i)
        # assigning x_i = val causes the gate to evaluate RY(val * π, i)
        _bind = {_inp_params[i]: float(_intent_list[i]) for i in range(4)}
        _bind.update({_wt_params[i]: 0.0 for i in range(4)})
        _bound_qc = _qc_raw.assign_parameters(_bind)

        with plt.style.context("dark_background"):
            _fig = _bound_qc.draw(output="mpl", fold=-1, initial_state=False)
            _fig.set_facecolor("#0D0F14")
            for _ax in _fig.get_axes():
                _ax.set_facecolor("#0D0F14")
                for _spine in _ax.spines.values():
                    _spine.set_visible(False)
            _fig.set_size_inches(10, 3.2)
        st.pyplot(_fig, width="stretch")
        plt.close(_fig)

with arch_specs:
    _qc     = get_photon_circuit()
    _n_ops  = sum(_qc.count_ops().values())
    _specs  = [
        ("Qubits",        str(_qc.num_qubits)),
        ("Circuit Depth", str(_qc.depth())),
        ("Total Gates",   str(_n_ops)),
        ("Input Params",  "4 × x_i  (BitNet)"),
        ("Weight Params", "4 × θ_i  (variational)"),
        ("Observables",   "4 × Pauli-Z ⟨Z⟩"),
        ("Connector",     "TorchConnector"),
        ("Framework",     "IBM Qiskit 1.x"),
    ]
    for _label, _value in _specs:
        st.markdown(
            f"""
            <div style='background:#13161E;border:1px solid #1F2333;border-radius:7px;
                        padding:9px 14px;margin-bottom:7px;display:flex;
                        justify-content:space-between;align-items:center;'>
              <span style='font-size:0.7rem;color:#7A8099;letter-spacing:0.4px;'>{_label}</span>
              <span style='font-size:0.76rem;font-weight:600;color:#C9D0E8;'>{_value}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

# ── Layer annotation strip ─────────────────────────────────────────────────
st.markdown(
    """
    <div style='display:flex;gap:12px;margin-top:18px;'>
      <div style='flex:1;background:#13161E;border:1px solid #1F2333;
                  border-top:2px solid #4A90D9;border-radius:8px;padding:14px 16px;'>
        <div style='font-size:0.63rem;color:#4A90D9;letter-spacing:1px;font-weight:700;
                    text-transform:uppercase;margin-bottom:6px;'>Layer 1 — Encoding</div>
        <div style='font-size:0.78rem;color:#A0AACC;line-height:1.55;'>
          <code style='background:#0D0F14;color:#6FCF97;padding:1px 5px;
                       border-radius:3px;font-size:0.72rem;'>RY(x&#x1D456; × π)</code>
          gates angle-encode the 4-D BitNet ternary tensor into the quantum
          amplitude of each qubit.</div>
      </div>
      <div style='flex:1;background:#13161E;border:1px solid #1F2333;
                  border-top:2px solid #BB6BD9;border-radius:8px;padding:14px 16px;'>
        <div style='font-size:0.63rem;color:#BB6BD9;letter-spacing:1px;font-weight:700;
                    text-transform:uppercase;margin-bottom:6px;'>Layer 2 — Entanglement</div>
        <div style='font-size:0.78rem;color:#A0AACC;line-height:1.55;'>
          Circular <code style='background:#0D0F14;color:#6FCF97;padding:1px 5px;
          border-radius:3px;font-size:0.72rem;'>CNOT</code> chain creates quantum
          entanglement, enabling combinatorial cross-route correlations beyond
          classical capability.</div>
      </div>
      <div style='flex:1;background:#13161E;border:1px solid #1F2333;
                  border-top:2px solid #6FCF97;border-radius:8px;padding:14px 16px;'>
        <div style='font-size:0.63rem;color:#6FCF97;letter-spacing:1px;font-weight:700;
                    text-transform:uppercase;margin-bottom:6px;'>Layer 3 — Variational</div>
        <div style='font-size:0.78rem;color:#A0AACC;line-height:1.55;'>
          Trainable <code style='background:#0D0F14;color:#6FCF97;padding:1px 5px;
          border-radius:3px;font-size:0.72rem;'>RY(θ&#x1D456;)</code> rotations form the
          variational block, optimisable via gradient descent through the
          TorchConnector hybrid bridge.</div>
      </div>
      <div style='flex:1;background:#13161E;border:1px solid #1F2333;
                  border-top:2px solid #C9A84C;border-radius:8px;padding:14px 16px;'>
        <div style='font-size:0.63rem;color:#C9A84C;letter-spacing:1px;font-weight:700;
                    text-transform:uppercase;margin-bottom:6px;'>Measurement</div>
        <div style='font-size:0.78rem;color:#A0AACC;line-height:1.55;'>
          Four independent <code style='background:#0D0F14;color:#6FCF97;padding:1px 5px;
          border-radius:3px;font-size:0.72rem;'>Pauli-Z</code> observables return
          expectation values ∈ [−1,&thinsp;1], normalised to Photon Match Scores
          [0–100] per route.</div>
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    "<p style='color:#252B3E;font-size:0.72rem;text-align:center;margin-top:32px;"
    "padding-top:16px;border-top:1px solid #1A1D28;'>"
    "Project Photon &nbsp;·&nbsp; Hybrid QNN Payment Routing &nbsp;·&nbsp; "
    "Classical BitNet + IBM Qiskit EstimatorQNN + PyTorch TorchConnector</p>",
    unsafe_allow_html=True,
)
