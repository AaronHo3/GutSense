"""
Seed patient profiles for demo. Each profile has a name, demographics,
and an archetype that drives the biomarker simulation.
Archetypes: "healthy" | "at_risk" | "critical"
"""

DEMO_PATIENTS = [
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
        "drift": True,  # markers trending upward over time
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
]
