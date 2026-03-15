"""
Seed patient profiles for demo. Each profile has a name, demographics,
and an archetype that drives the biomarker simulation.
Archetypes: "healthy" | "at_risk" | "critical"
"""

DEMO_PATIENTS = [
    # ── Original 5 ──────────────────────────────────────────────────────────────
    {
        "name": "Alice Chen",
        "age": 45,
        "sex": "F",
        "family_history": False,
        "has_nod2_variant": False,
        "archetype": "healthy",
    },
    {
        "name": "Bob Martinez",
        "age": 58,
        "sex": "M",
        "family_history": True,
        "has_nod2_variant": False,
        "archetype": "at_risk",
        "drift": True,
    },
    {
        "name": "Carol Wang",
        "age": 62,
        "sex": "F",
        "family_history": False,
        "has_nod2_variant": False,
        "archetype": "at_risk",
        "drift": False,
    },
    {
        "name": "David Kim",
        "age": 51,
        "sex": "M",
        "family_history": True,
        "has_nod2_variant": True,
        "archetype": "critical",
    },
    {
        "name": "Emma Johnson",
        "age": 38,
        "sex": "F",
        "family_history": False,
        "has_nod2_variant": False,
        "archetype": "healthy",
    },

    # ── 4 Green (healthy) ────────────────────────────────────────────────────────
    {
        "name": "James Patel",
        "age": 34,
        "sex": "M",
        "family_history": False,
        "has_nod2_variant": False,
        "archetype": "healthy",
    },
    {
        "name": "Sophia Rodriguez",
        "age": 41,
        "sex": "F",
        "family_history": False,
        "has_nod2_variant": False,
        "archetype": "healthy",
    },
    {
        "name": "Michael Thompson",
        "age": 29,
        "sex": "M",
        "family_history": False,
        "has_nod2_variant": False,
        "archetype": "healthy",
    },
    {
        "name": "Lauren Kim",
        "age": 52,
        "sex": "F",
        "family_history": False,
        "has_nod2_variant": False,
        "archetype": "healthy",
    },

    # ── 4 Yellow (at_risk) ───────────────────────────────────────────────────────
    {
        "name": "Robert Harris",
        "age": 55,
        "sex": "M",
        "family_history": True,
        "has_nod2_variant": False,
        "archetype": "at_risk",
    },
    {
        "name": "Jennifer Liu",
        "age": 48,
        "sex": "F",
        "family_history": False,
        "has_nod2_variant": False,
        "archetype": "at_risk",
        "drift": True,
    },
    {
        "name": "William Brown",
        "age": 63,
        "sex": "M",
        "family_history": True,
        "has_nod2_variant": False,
        "archetype": "at_risk",
    },
    {
        "name": "Patricia Garcia",
        "age": 44,
        "sex": "F",
        "family_history": False,
        "has_nod2_variant": False,
        "archetype": "at_risk",
    },

    # ── 2 Red (critical) ─────────────────────────────────────────────────────────
    {
        "name": "Charles Wilson",
        "age": 67,
        "sex": "M",
        "family_history": True,
        "has_nod2_variant": True,
        "archetype": "critical",
    },
    {
        "name": "Nancy Davis",
        "age": 59,
        "sex": "F",
        "family_history": True,
        "has_nod2_variant": False,
        "archetype": "critical",
    },
]
