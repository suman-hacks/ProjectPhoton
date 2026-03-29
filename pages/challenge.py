"""
pages/challenge.py — Project Photon: Executive Challenge
"What Would You Do?" — 3-round routing decision game for leadership demos.
"""

import streamlit as st
from mock_data import SCENARIOS, ROUTES, BADGE_COLORS
from bitnet_encoder import extract_intent_vector
from qiskit_router import build_qnn_model, score_routes

SCENARIO_ORDER = ["A", "B", "C"]

# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------
_DEFAULTS = {
    "ch_round":       0,           # 0, 1, 2
    "ch_phase":       "pick",      # "pick" | "reveal" | "complete"
    "ch_human_picks": [],          # list of route IDs chosen per round
    "ch_results":     [],          # list of result dicts per round
}
for k, v in _DEFAULTS.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ---------------------------------------------------------------------------
# QNN model — reuse cached instance from dashboard if already built
# ---------------------------------------------------------------------------
@st.cache_resource(show_spinner=False)
def get_qnn_model():
    return build_qnn_model()

# ---------------------------------------------------------------------------
# CSS
# ---------------------------------------------------------------------------
st.markdown("""
<style>
  html, body, [data-testid="stAppViewContainer"] {
      background-color: #0D0F14;
      color: #E8EAF0;
      font-family: 'Inter', 'Segoe UI', sans-serif;
  }
  [data-testid="stSidebar"] {
      background-color: #13161E;
      border-right: 1px solid #1F2333;
  }
  h1 { color: #FFFFFF; letter-spacing: -0.5px; }
  h2 { color: #C9D0E8; font-size: 1.1rem; font-weight: 600; }

  .ch-route-card {
      background: linear-gradient(145deg, #161A26, #1C2133);
      border: 1px solid #252B3E;
      border-radius: 12px;
      padding: 20px 22px;
      margin-bottom: 4px;
      transition: border-color 0.2s;
  }
  .ch-route-card.selected {
      border-color: #4A90D9;
      box-shadow: 0 0 20px #4A90D922;
  }
  .ch-route-card.photon-winner {
      border-color: #C9A84C;
      box-shadow: 0 0 24px #C9A84C22;
  }
  .ch-route-card.human-match {
      border-color: #6FCF97;
      box-shadow: 0 0 20px #6FCF9722;
  }
  .route-badge {
      display: inline-block;
      font-size: 0.62rem;
      font-weight: 700;
      letter-spacing: 1.2px;
      padding: 3px 9px;
      border-radius: 4px;
      margin-bottom: 10px;
  }
  .stat-row { display: flex; gap: 8px; flex-wrap: wrap; margin-top: 12px; }
  .stat-pill {
      background: #0D0F14;
      border: 1px solid #252B3E;
      border-radius: 8px;
      padding: 7px 12px;
      font-size: 0.76rem;
      text-align: center;
      flex: 1;
      min-width: 68px;
  }
  .stat-pill .label { color: #7A8099; font-size: 0.63rem; letter-spacing: 0.8px; text-transform: uppercase; }
  .stat-pill .value { color: #E8EAF0; font-size: 1.0rem; font-weight: 600; margin-top: 2px; }
  .stat-pill.quantum .label { color: #7B6FA8; }
  .stat-pill.quantum .value { color: #C9A84C; font-size: 1.1rem; }

  .scenario-box {
      background: #13161E;
      border: 1px solid #1F2333;
      border-radius: 10px;
      padding: 20px 24px;
      margin-bottom: 24px;
  }
  .scenario-box .amount { font-size: 2rem; font-weight: 700; color: #FFFFFF; }
  .scenario-box .meta   { font-size: 0.82rem; color: #7A8099; margin-top: 6px; }
  .scenario-box .desc   { font-size: 0.88rem; color: #A0AACC; margin-top: 10px; line-height: 1.6; }

  .reveal-box {
      border-radius: 12px;
      padding: 24px 28px;
      margin: 20px 0;
  }
  .reveal-box.match {
      background: linear-gradient(135deg, #0D1A12, #122018);
      border: 1px solid #6FCF97;
  }
  .reveal-box.no-match {
      background: linear-gradient(135deg, #14101A, #1A1428);
      border: 1px solid #C9A84C;
  }

  .delta-card {
      background: #0D0F14;
      border: 1px solid #252B3E;
      border-radius: 10px;
      padding: 16px 20px;
      text-align: center;
  }
  .delta-card .d-label { font-size: 0.68rem; color: #7A8099; text-transform: uppercase; letter-spacing: 0.8px; }
  .delta-card .d-value { font-size: 1.5rem; font-weight: 700; color: #C9A84C; margin-top: 4px; }
  .delta-card .d-sub   { font-size: 0.72rem; color: #A0AACC; margin-top: 3px; }

  .scoreboard-row {
      background: #13161E;
      border: 1px solid #1F2333;
      border-radius: 10px;
      padding: 14px 20px;
      margin-bottom: 8px;
      display: flex;
      align-items: center;
      gap: 16px;
  }

  .progress-bar-track {
      background: #1C2133;
      border-radius: 4px;
      height: 6px;
      margin-top: 8px;
      overflow: hidden;
  }
  .progress-bar-fill {
      height: 100%;
      border-radius: 4px;
      background: linear-gradient(90deg, #7B6FA8, #C9A84C);
  }

  .badge-banner {
      border-radius: 12px;
      padding: 28px;
      text-align: center;
      margin: 24px 0;
  }
  .stage-label {
      font-size: 0.65rem;
      font-weight: 700;
      letter-spacing: 2px;
      color: #7A8099;
      text-transform: uppercase;
      margin-bottom: 6px;
  }

  /* ── Top header bar ── */
  header[data-testid="stHeader"] {
      background-color: #0D0F14 !important;
      border-bottom: 1px solid #1F2333;
  }
  [data-testid="stToolbar"]        { background-color: #0D0F14 !important; }
  [data-testid="stToolbarActions"] { display: none !important; }
  #MainMenu { visibility: hidden !important; }

  /* ── Sidebar nav link visibility ── */
  [data-testid="stSidebarNavLink"] span,
  [data-testid="stSidebarNavLink"] p,
  [data-testid="stSidebarNavLink"] {
      color: #C9D0E8 !important;
  }
  [data-testid="stSidebarNavLink"]:hover span,
  [data-testid="stSidebarNavLink"]:hover p {
      color: #FFFFFF !important;
  }
  [data-testid="stSidebarNavLink"][aria-selected="true"] span,
  [data-testid="stSidebarNavLink"][aria-selected="true"] p {
      color: #C9A84C !important;
  }
  section[data-testid="stSidebar"] a,
  section[data-testid="stSidebar"] span {
      color: #C9D0E8;
  }
</style>
""", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _run_photon(scenario: dict) -> list:
    """Run QNN scoring for a scenario using fallback intent vector (fast, deterministic)."""
    model = get_qnn_model()
    intent_tensor, _, _ = extract_intent_vector(scenario, None, None, None)
    return score_routes(model, intent_tensor, ROUTES, scenario_data=scenario)


def _compute_delta(human_route: dict, photon_route: dict, amount_usd: float) -> dict:
    """Compute financial and performance delta between human pick and Photon's winner."""
    h = human_route["stats"]
    p = photon_route["stats"]

    fee_delta_usd   = (h["cost_bps"] - p["cost_bps"]) / 10_000 * amount_usd
    approval_delta  = p["approval_rate"] - h["approval_rate"]
    latency_delta   = h["latency_ms"] - p["latency_ms"]
    resilience_delta = p["resilience_score"] - h["resilience_score"]

    return {
        "fee_delta_usd":    fee_delta_usd,
        "approval_delta":   approval_delta,
        "latency_delta":    latency_delta,
        "resilience_delta": resilience_delta,
    }


def _route_rank(route_id: str, scored: list) -> int:
    """Return 1-based rank of a route in the scored list (1 = best)."""
    for i, r in enumerate(scored):
        if r["id"] == route_id:
            return i + 1
    return 4


def _round_points(rank: int) -> int:
    return {1: 3, 2: 2, 3: 1, 4: 0}.get(rank, 0)


def _badge_for_score(total: int) -> tuple:
    """Return (title, color, description) for final score badge."""
    if total >= 8:
        return "Quantum Strategist", "#C9A84C", "Your instincts align with the quantum layer. You think in optimization."
    elif total >= 5:
        return "Strong Commercial Instincts", "#4A90D9", "Solid judgment across most scenarios. The machine refined the edge cases."
    elif total >= 3:
        return "Learning the Signal", "#6FCF97", "Good intuition on some dimensions. Photon sees the full combinatorial picture."
    else:
        return "Let the Machine Drive", "#BB6BD9", "Complex multi-variable optimization is exactly where quantum routing excels."


def _render_route_card(route: dict, is_selected: bool = False, extra_class: str = "") -> str:
    badge_color = BADGE_COLORS.get(route["badge"], "#7A8099")
    s = route["stats"]
    css_class = "ch-route-card"
    if extra_class:
        css_class += f" {extra_class}"
    elif is_selected:
        css_class += " selected"

    photon_pill = ""
    if "photon_score" in route:
        photon_pill = (
            '<div class="stat-pill quantum">'
            '<div class="label">⚛ Photon</div>'
            f'<div class="value">{route["photon_score"]}</div>'
            '</div>'
        )

    pill = lambda label, val: (
        f'<div class="stat-pill">'
        f'<div class="label">{label}</div>'
        f'<div class="value">{val}</div>'
        f'</div>'
    )

    return (
        f'<div class="{css_class}">'
        f'<div><span class="route-badge" style="background:{badge_color}22;color:{badge_color};border:1px solid {badge_color}44;">'
        f'{route["badge"]}</span></div>'
        f'<div style="font-size:1.0rem;font-weight:700;color:#E8EAF0;">{route["name"]}</div>'
        f'<div style="font-size:0.78rem;color:#7A8099;margin-top:4px;">{route["description"]}</div>'
        f'<div class="stat-row">'
        + pill("Approval", f'{s["approval_rate"]}%')
        + pill("Cost", f'{s["cost_bps"]} bps')
        + pill("Latency", f'{s["latency_ms"]}ms')
        + pill("Resilience", str(s["resilience_score"]))
        + photon_pill
        + '</div></div>'
    )


# ---------------------------------------------------------------------------
# Reset
# ---------------------------------------------------------------------------
def _reset():
    for k, v in _DEFAULTS.items():
        st.session_state[k] = v if not isinstance(v, list) else []


# ---------------------------------------------------------------------------
# Page header
# ---------------------------------------------------------------------------
col_title, col_reset = st.columns([5, 1])
with col_title:
    st.markdown('<div class="stage-label">Executive Challenge</div>', unsafe_allow_html=True)
    st.markdown("## What Would You Do?")
    st.markdown(
        '<p style="color:#7A8099; font-size:0.88rem; margin-top:-8px;">'
        'Three real payment scenarios. Pick the route you would authorize. '
        'Then see what Project Photon chose — and why.'
        '</p>',
        unsafe_allow_html=True,
    )
with col_reset:
    st.markdown("<div style='padding-top:28px'>", unsafe_allow_html=True)
    if st.button("↺ Restart", use_container_width=True):
        _reset()
        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

# Progress dots
round_idx = st.session_state.ch_round
phase     = st.session_state.ch_phase

dots = ""
for i in range(3):
    if i < round_idx or phase == "complete":
        dots += '<span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:#C9A84C;margin-right:6px;"></span>'
    elif i == round_idx and phase != "complete":
        dots += '<span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:#4A90D9;margin-right:6px;"></span>'
    else:
        dots += '<span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:#252B3E;margin-right:6px;"></span>'

label = "Complete" if phase == "complete" else f"Round {round_idx + 1} of 3"
st.markdown(
    f'<div style="margin:8px 0 28px 0;">{dots}'
    f'<span style="font-size:0.75rem; color:#7A8099; vertical-align:middle;">{label}</span></div>',
    unsafe_allow_html=True,
)

st.divider()

# ---------------------------------------------------------------------------
# COMPLETE screen
# ---------------------------------------------------------------------------
if phase == "complete":
    total_pts = sum(r["points"] for r in st.session_state.ch_results)
    max_pts   = 9
    pct       = total_pts / max_pts

    title, color, desc = _badge_for_score(total_pts)

    st.markdown(
        f'<div class="badge-banner" style="background:linear-gradient(135deg,#13161E,#1C2133);border:2px solid {color};">'
        f'<div style="font-size:2.8rem; font-weight:800; color:{color};">{total_pts}<span style="font-size:1.2rem;color:#7A8099;">/{max_pts}</span></div>'
        f'<div style="font-size:1.3rem; font-weight:700; color:#FFFFFF; margin-top:8px;">{title}</div>'
        f'<div style="font-size:0.85rem; color:#A0AACC; margin-top:8px; max-width:480px; margin-left:auto; margin-right:auto;">{desc}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    st.markdown("### Round-by-Round Recap")

    medals = ["🥇", "🥈", "🥉"]
    for i, res in enumerate(st.session_state.ch_results):
        sc  = SCENARIOS[SCENARIO_ORDER[i]]
        matched = res["human_id"] == res["photon_id"]
        status_icon  = "✓" if matched else "✗"
        status_color = "#6FCF97" if matched else "#C9A84C"
        outcome_text = "Matched Photon" if matched else f"Photon: {res['photon_name']}"

        st.markdown(
            f'<div class="scoreboard-row">'
            f'<span style="font-size:1.4rem;">{medals[i]}</span>'
            f'<div style="flex:1;">'
            f'  <div style="font-size:0.88rem;font-weight:600;color:#E8EAF0;">{sc["label"]}</div>'
            f'  <div style="font-size:0.75rem;color:#7A8099;">You chose: {res["human_name"]} · {outcome_text}</div>'
            f'</div>'
            f'<div style="text-align:right;">'
            f'  <span style="font-size:1.1rem;font-weight:700;color:{status_color};">'
            f'    {status_icon} {res["points"]}/3 pts'
            f'  </span>'
            f'</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

    bar_w = int(pct * 100)
    st.markdown(
        f'<div class="progress-bar-track"><div class="progress-bar-fill" style="width:{bar_w}%;"></div></div>'
        f'<div style="font-size:0.72rem;color:#7A8099;margin-top:6px;text-align:right;">{total_pts}/{max_pts} points</div>',
        unsafe_allow_html=True,
    )

    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("Play Again", type="primary", use_container_width=False):
        _reset()
        st.rerun()

    st.stop()

# ---------------------------------------------------------------------------
# Active round
# ---------------------------------------------------------------------------
scenario_id  = SCENARIO_ORDER[round_idx]
scenario     = SCENARIOS[scenario_id]
amount       = scenario["amount_usd"]
amount_fmt   = f"${amount:,.0f}"

st.markdown(
    f'<div class="scenario-box">'
    f'<div class="stage-label">Round {round_idx + 1} · {scenario["label"]}</div>'
    f'<div class="amount">{amount_fmt}</div>'
    f'<div class="meta">{scenario["currency_pair"]} &nbsp;·&nbsp; Risk: {scenario["risk_tier"]}</div>'
    f'<div class="desc">{scenario["description"]}</div>'
    f'</div>',
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# PICK phase — show selectable route cards
# ---------------------------------------------------------------------------
if phase == "pick":
    st.markdown(
        '<p style="font-size:0.9rem;color:#A0AACC;margin-bottom:16px;">'
        '<strong style="color:#E8EAF0;">Select the route you would authorize</strong> — '
        'all four stats are visible. Photon\'s scores are hidden until you commit.'
        '</p>',
        unsafe_allow_html=True,
    )

    cols = st.columns(2)
    for idx, route in enumerate(ROUTES):
        col = cols[idx % 2]
        with col:
            st.markdown(_render_route_card(route), unsafe_allow_html=True)
            if st.button(f"Select: {route['name']}", key=f"pick_{route['id']}", use_container_width=True):
                st.session_state.ch_human_picks.append(route["id"])
                st.session_state.ch_phase = "reveal"
                st.rerun()

# ---------------------------------------------------------------------------
# REVEAL phase — show result
# ---------------------------------------------------------------------------
elif phase == "reveal":
    human_id     = st.session_state.ch_human_picks[round_idx]
    human_route  = next(r for r in ROUTES if r["id"] == human_id)

    with st.spinner("Running Photon QNN..."):
        scored = _run_photon(scenario)

    photon_route = scored[0]   # top-ranked
    photon_id    = photon_route["id"]
    matched      = human_id == photon_id
    human_rank   = _route_rank(human_id, scored)
    points       = _round_points(human_rank)
    delta        = _compute_delta(human_route, photon_route, amount)

    # Store result
    if len(st.session_state.ch_results) <= round_idx:
        st.session_state.ch_results.append({
            "human_id":    human_id,
            "human_name":  human_route["name"],
            "photon_id":   photon_id,
            "photon_name": photon_route["name"],
            "points":      points,
            "rank":        human_rank,
            "delta":       delta,
            "scored":      scored,
        })

    # ── Verdict banner ──────────────────────────────────────────────────
    if matched:
        st.markdown(
            '<div class="reveal-box match">'
            '<div style="font-size:1.4rem;font-weight:700;color:#6FCF97;">✓ You matched Photon</div>'
            '<div style="font-size:0.85rem;color:#A0AACC;margin-top:6px;">'
            'Your instinct aligned with the quantum-optimized decision. '
            f'<strong style="color:#6FCF97;">+{points} points</strong></div>'
            '</div>',
            unsafe_allow_html=True,
        )
    else:
        fee_str = (
            f"${abs(delta['fee_delta_usd']):,.0f} in fees"
            if delta["fee_delta_usd"] > 0
            else f"${abs(delta['fee_delta_usd']):,.0f} additional cost"
        )
        st.markdown(
            f'<div class="reveal-box no-match">'
            f'<div style="font-size:1.4rem;font-weight:700;color:#C9A84C;">⚛ Photon chose differently</div>'
            f'<div style="font-size:0.85rem;color:#A0AACC;margin-top:6px;">'
            f'You selected <strong style="color:#E8EAF0;">{human_route["name"]}</strong> (Rank #{human_rank}). '
            f'Photon selected <strong style="color:#C9A84C;">{photon_route["name"]}</strong>. '
            f'<strong style="color:#C9A84C;">+{points} points</strong></div>'
            f'</div>',
            unsafe_allow_html=True,
        )

    # ── Delta metrics ────────────────────────────────────────────────────
    if not matched:
        st.markdown("#### Why Photon's Route Wins This Scenario")
        d1, d2, d3, d4 = st.columns(4)

        fee_val = delta["fee_delta_usd"]
        with d1:
            sign = "saved" if fee_val > 0 else "costs"
            st.markdown(
                f'<div class="delta-card">'
                f'<div class="d-label">Fee Impact</div>'
                f'<div class="d-value" style="color:{"#6FCF97" if fee_val>0 else "#F2994A"};">'
                f'{"+" if fee_val>0 else "-"}${abs(fee_val):,.0f}</div>'
                f'<div class="d-sub">Photon {sign} in transaction fees</div>'
                f'</div>',
                unsafe_allow_html=True,
            )
        with d2:
            av = delta["approval_delta"]
            st.markdown(
                f'<div class="delta-card">'
                f'<div class="d-label">Approval Rate</div>'
                f'<div class="d-value" style="color:{"#6FCF97" if av>=0 else "#F2994A"};">'
                f'{av:+.1f}%</div>'
                f'<div class="d-sub">{"Higher" if av>=0 else "Lower"} approval probability</div>'
                f'</div>',
                unsafe_allow_html=True,
            )
        with d3:
            lv = delta["latency_delta"]
            st.markdown(
                f'<div class="delta-card">'
                f'<div class="d-label">Latency</div>'
                f'<div class="d-value" style="color:{"#6FCF97" if lv>=0 else "#F2994A"};">'
                f'{lv:+d}ms</div>'
                f'<div class="d-sub">{"Faster" if lv>=0 else "Slower"} settlement</div>'
                f'</div>',
                unsafe_allow_html=True,
            )
        with d4:
            rv = delta["resilience_delta"]
            st.markdown(
                f'<div class="delta-card">'
                f'<div class="d-label">Resilience</div>'
                f'<div class="d-value" style="color:{"#6FCF97" if rv>=0 else "#F2994A"};">'
                f'{rv:+d}</div>'
                f'<div class="d-sub">{"Better" if rv>=0 else "Lower"} failover score</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

    # ── Full ranking reveal ───────────────────────────────────────────────
    st.markdown("#### Full Photon Ranking")
    rank_medals = {1: "🥇", 2: "🥈", 3: "🥉", 4: "4th"}
    rcols = st.columns(4)
    for ri, sr in enumerate(scored):
        is_photon = sr["id"] == photon_id
        is_human  = sr["id"] == human_id
        extra = "photon-winner" if is_photon else ("human-match" if is_human and matched else "")
        if is_human and is_photon:
            tag = '<div style="font-size:0.65rem;color:#6FCF97;font-weight:700;margin-bottom:6px;letter-spacing:1px;">✓ MATCH</div>'
        elif is_photon:
            tag = '<div style="font-size:0.65rem;color:#C9A84C;font-weight:700;margin-bottom:6px;letter-spacing:1px;">⚛ PHOTON CHOICE</div>'
        elif is_human:
            tag = '<div style="font-size:0.65rem;color:#4A90D9;font-weight:700;margin-bottom:6px;letter-spacing:1px;">YOUR PICK</div>'
        else:
            tag = ""
        with rcols[ri]:
            # Two separate st.markdown calls to avoid 4-space code-block interpretation
            st.markdown(
                f'<div style="text-align:center;font-size:1.4rem;margin-bottom:4px;">{rank_medals[ri+1]}</div>'
                + tag,
                unsafe_allow_html=True,
            )
            st.markdown(_render_route_card(sr, extra_class=extra), unsafe_allow_html=True)

    # ── Navigation ────────────────────────────────────────────────────────
    st.markdown("<br>", unsafe_allow_html=True)
    running_pts = sum(r["points"] for r in st.session_state.ch_results)

    bottom_left, bottom_right = st.columns([3, 1])
    with bottom_left:
        st.markdown(
            f'<div style="font-size:0.82rem;color:#7A8099;padding-top:10px;">'
            f'Running score: <strong style="color:#C9A84C;">{running_pts} pts</strong> after {round_idx+1} round(s)</div>',
            unsafe_allow_html=True,
        )
    with bottom_right:
        next_label = "Final Results →" if round_idx == 2 else f"Round {round_idx + 2} →"
        if st.button(next_label, type="primary", use_container_width=True):
            if round_idx >= 2:
                st.session_state.ch_phase = "complete"
            else:
                st.session_state.ch_round += 1
                st.session_state.ch_phase = "pick"
            st.rerun()
