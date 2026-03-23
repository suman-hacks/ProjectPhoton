"""
mock_data.py — Project Photon
Synthetic payment scenarios and static route candidates used across all phases.
"""

# ---------------------------------------------------------------------------
# Payment Scenarios
# Each scenario defines the business context and the priority weights that
# the BitNet encoder will later confirm or refine.
# ---------------------------------------------------------------------------

SCENARIOS = {
    "A": {
        "id": "A",
        "label": "High-Value Cross-Border",
        "description": (
            "A $2.4M interbank settlement between New York and Singapore. "
            "Counterparty risk is moderate; the treasury desk requires a guaranteed "
            "approval path with acceptable cost. Latency is secondary."
        ),
        "priority_hint": {
            "approval": "HIGH",
            "cost": "BALANCED",
            "latency": "LOW",
            "resilience": "MEDIUM",
        },
        "amount_usd": 2_400_000,
        "currency_pair": "USD → SGD",
        "risk_tier": "Moderate",
    },
    "B": {
        "id": "B",
        "label": "Domestic Instant / RTP",
        "description": (
            "A $12,500 real-time payment between two retail accounts on the FedNow "
            "network. SLA demands sub-second settlement. Cost is negligible; "
            "any latency above 800ms is a breach of contract."
        ),
        "priority_hint": {
            "approval": "MEDIUM",
            "cost": "LOW",
            "latency": "CRITICAL",
            "resilience": "LOW",
        },
        "amount_usd": 12_500,
        "currency_pair": "USD → USD",
        "risk_tier": "Low",
    },
    "C": {
        "id": "C",
        "label": "High-Risk Merchant Authorization",
        "description": (
            "A $87,000 card-not-present authorization for a high-chargeback merchant "
            "in the gaming vertical. Primary network exposure is elevated; the system "
            "must prioritize failover resilience and network redundancy above all else."
        ),
        "priority_hint": {
            "approval": "MEDIUM",
            "cost": "LOW",
            "latency": "MEDIUM",
            "resilience": "CRITICAL",
        },
        "amount_usd": 87_000,
        "currency_pair": "USD → EUR",
        "risk_tier": "High",
    },
}

# ---------------------------------------------------------------------------
# Route Candidates
# Four static routes evaluated for every scenario. Stats represent raw
# network benchmarks before quantum optimization scoring is applied.
# ---------------------------------------------------------------------------

ROUTES = [
    {
        "id": "R1",
        "name": "Direct Issuer Connect",
        "description": "Bilateral link to the issuing bank. Highest approval rate but no fallback path.",
        "stats": {
            "approval_rate": 98.2,   # %
            "cost_bps": 4.5,         # basis points
            "latency_ms": 310,       # milliseconds
            "resilience_score": 61,  # 0–100
        },
        "badge": "PREMIUM",
    },
    {
        "id": "R2",
        "name": "Network Alpha (Visa+)",
        "description": "Tier-1 card network with global reach, strong SLAs, and broad acceptance.",
        "stats": {
            "approval_rate": 95.7,
            "cost_bps": 8.2,
            "latency_ms": 185,
            "resilience_score": 84,
        },
        "badge": "STANDARD",
    },
    {
        "id": "R3",
        "name": "Least-Cost Processor",
        "description": "Regional acquirer optimized for domestic volume. Minimal fees, limited global reach.",
        "stats": {
            "approval_rate": 88.4,
            "cost_bps": 1.8,
            "latency_ms": 420,
            "resilience_score": 55,
        },
        "badge": "ECONOMY",
    },
    {
        "id": "R4",
        "name": "Resilient Fallback Network",
        "description": "Multi-path redundant rail with automatic failover. Built for high-risk and cross-border flows.",
        "stats": {
            "approval_rate": 91.3,
            "cost_bps": 11.4,
            "latency_ms": 540,
            "resilience_score": 97,
        },
        "badge": "RESILIENT",
    },
]

# Badge color mapping used by the UI
BADGE_COLORS = {
    "PREMIUM":   "#C9A84C",   # gold
    "STANDARD":  "#4A90D9",   # blue
    "ECONOMY":   "#6FCF97",   # green
    "RESILIENT": "#BB6BD9",   # purple
}
