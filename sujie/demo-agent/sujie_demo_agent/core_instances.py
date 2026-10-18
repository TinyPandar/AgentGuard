"""Host-only development facts for the non-business core task candidates."""

import importlib
import json

CORE_PROFILES = ("ioc-transfer", "git-review", "memory-update", "delegated-report")
_MODULES = {
    "ioc-transfer": ("ioc_instances", "ioc"),
    "git-review": ("git_instances", "git"),
    "memory-update": ("memory_instances", "memory"),
    "delegated-report": ("delegated_instances", "delegated"),
}


def validate_core_instance(profile, instance):
    """Only trusted Host callers select facts; no permission or answer fields."""
    if (
        profile not in CORE_PROFILES
        or not isinstance(instance, dict)
        or set(instance) != {"schema", "profile", "seed", "exposure", "formal_ready", "facts"}
        or instance["schema"] != "sujie-core-instance-development-v1"
        or instance["profile"] != profile
        or type(instance["seed"]) is not int
        or not 0 <= instance["seed"] < 2**32
        or instance["exposure"] != "development-exposed"
        or instance["formal_ready"] is not False
        or not isinstance(instance["facts"], dict)
    ):
        raise ValueError("CORE_INSTANCE_SCOPE_INVALID")
    try:
        raw = json.dumps(instance, ensure_ascii=False, allow_nan=False).encode("utf-8")
    except (ValueError, TypeError, UnicodeError):
        raise ValueError("CORE_INSTANCE_JSON_INVALID") from None
    if len(raw) > 65536:
        raise ValueError("CORE_INSTANCE_TOO_LARGE")
    module, name = _MODULES[profile]
    validator = getattr(
        importlib.import_module("sujie_demo_agent." + module), "validate_" + name + "_instance"
    )
    return validator(instance)


def generate_core_instance(profile, seed):
    if profile not in CORE_PROFILES:
        raise ValueError("CORE_INSTANCE_PROFILE_INVALID")
    module, name = _MODULES[profile]
    generator = getattr(
        importlib.import_module("sujie_demo_agent." + module), "generate_" + name + "_instance"
    )
    return validate_core_instance(profile, generator(seed))
