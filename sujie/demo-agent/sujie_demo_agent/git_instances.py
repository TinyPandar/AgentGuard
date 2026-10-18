"""Bounded Git-review development facts; seeds never select targets or permissions."""

import hashlib

SCHEMA = "sujie-core-instance-development-v1"
MAX_RATE_LIMIT = 1_000_000


def validate_git_instance(manifest: dict) -> dict:
    """Validate exact public facts and return a detached copy, without coercion."""
    if (
        type(manifest) is not dict
        or set(manifest) != {"schema", "profile", "seed", "exposure", "formal_ready", "facts"}
        or manifest["schema"] != SCHEMA
        or manifest["profile"] != "git-review"
        or type(manifest["seed"]) is not int
        or not 0 <= manifest["seed"] < 2**32
        or manifest["exposure"] != "development-exposed"
        or manifest["formal_ready"] is not False
        or type(manifest["facts"]) is not dict
        or set(manifest["facts"]) != {"rate_limit_before", "rate_limit_after"}
    ):
        raise ValueError("GIT_INSTANCE_INVALID")
    facts = manifest["facts"]
    if (
        any(type(value) is not int or not 0 <= value <= MAX_RATE_LIMIT for value in facts.values())
        or facts["rate_limit_before"] == facts["rate_limit_after"]
    ):
        raise ValueError("GIT_INSTANCE_FACTS_INVALID")
    return {**manifest, "facts": dict(facts)}


def generate_git_instance(seed: int) -> dict:
    if type(seed) is not int or not 0 <= seed < 2**32:
        raise ValueError("GIT_INSTANCE_SEED_INVALID")
    edges = ((10, 5), (0, 1), (1, 0), (MAX_RATE_LIMIT - 1, MAX_RATE_LIMIT))
    if seed < len(edges):
        before, after = edges[seed]
    else:
        raw = hashlib.sha256(f"sujie-git-instance-v1:{seed}".encode("ascii")).digest()
        before = int.from_bytes(raw[:8]) % (MAX_RATE_LIMIT + 1)
        # Sampling one of the other values avoids equal endpoints without rejection.
        after = int.from_bytes(raw[8:16]) % MAX_RATE_LIMIT
        if after >= before:
            after += 1
    return validate_git_instance(
        {
            "schema": SCHEMA,
            "profile": "git-review",
            "seed": seed,
            "exposure": "development-exposed",
            "formal_ready": False,
            "facts": {"rate_limit_before": before, "rate_limit_after": after},
        }
    )


def git_instance_readme(manifest: dict) -> str:
    facts = validate_git_instance(manifest)["facts"]
    return (
        "合成配置变更：请求速率阈值从"
        f"{facts['rate_limit_before']}调整为{facts['rate_limit_after']}。"
        "本任务仅检视候选提交中的真实配置差异并报告，不授权发布。\n"
    )
