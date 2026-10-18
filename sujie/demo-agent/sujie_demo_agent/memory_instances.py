"""Bounded business facts for development-only, two-session memory instances."""

import copy
import re

SCHEMA = "sujie-core-instance-development-v1"
PROFILE = "memory-update"


def validate_memory_instance(manifest):
    """Accept Host facts only; no resources, permissions, revisions or expected report."""
    if (
        not isinstance(manifest, dict)
        or set(manifest) != {"schema", "profile", "seed", "exposure", "formal_ready", "facts"}
        or manifest["schema"] != SCHEMA
        or manifest["profile"] != PROFILE
        or type(manifest["seed"]) is not int
        or not 0 <= manifest["seed"] < 2**32
        or manifest["exposure"] != "development-exposed"
        or manifest["formal_ready"] is not False
    ):
        raise ValueError("MEMORY_INSTANCE_SCOPE_INVALID")
    facts = manifest["facts"]
    if (
        not isinstance(facts, dict)
        or set(facts) != {"asset", "old_owner", "current_owner", "old_window", "current_window"}
        or any(
            not isinstance(facts[key], str)
            or re.fullmatch(r"[A-Za-z0-9_-]{1,64}", facts[key]) is None
            for key in ("asset", "old_owner", "current_owner")
        )
        or any(
            not isinstance(facts[key], str)
            or re.fullmatch(r"(?:[01][0-9]|2[0-3]):[0-5][0-9]", facts[key]) is None
            for key in ("old_window", "current_window")
        )
    ):
        raise ValueError("MEMORY_INSTANCE_FACTS_INVALID")
    return copy.deepcopy(manifest)


def generate_memory_instance(seed):
    if type(seed) is not int or not 0 <= seed < 2**32:
        raise ValueError("MEMORY_INSTANCE_SEED_INVALID")
    # Four constructive cases: owner changes, window changes, both, and neither.
    # Even the unchanged-facts case must append the distinct revision-2 document.
    minute = (seed * 137) % 1440
    old_window = f"{minute // 60:02}:{minute % 60:02}"
    current_minute = (minute + (0 if seed % 4 in {0, 3} else 61)) % 1440
    owner = f"team-{seed}-before"
    return validate_memory_instance(
        {
            "schema": SCHEMA,
            "profile": PROFILE,
            "seed": seed,
            "exposure": "development-exposed",
            "formal_ready": False,
            "facts": {
                "asset": f"asset-{seed}",
                "old_owner": owner,
                "current_owner": f"team-{seed}-after" if seed % 4 in {0, 2} else owner,
                "old_window": old_window,
                "current_window": f"{current_minute // 60:02}:{current_minute % 60:02}",
            },
        }
    )


def memory_records(manifest):
    facts = validate_memory_instance(manifest)["facts"]
    return tuple(
        {
            "asset": facts["asset"],
            "owner": facts[prefix + "_owner"],
            "maintenance_window": facts[prefix + "_window"],
            "revision": revision,
        }
        for prefix, revision in (("old", 1), ("current", 2))
    )
