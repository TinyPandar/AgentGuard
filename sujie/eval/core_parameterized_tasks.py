"""Sealed, explicitly exposed development instances for admitted core candidates."""

import argparse
import hashlib
import json
import re
import stat
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "demo-agent"))

from parameterized_tasks import generate_instance as generate_business_instance  # noqa: E402
from sujie_demo_agent.business_workflows import validate_instance  # noqa: E402
from sujie_demo_agent.core_instances import (  # noqa: E402
    CORE_PROFILES,
    generate_core_instance,
    validate_core_instance,
)

BUSINESS_PROFILES = ("event-timeline", "attachment-audit")
PROFILES = (*BUSINESS_PROFILES, *CORE_PROFILES)


def encoded(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n"


def validate(instance):
    if not isinstance(instance, dict) or instance.get("profile") not in PROFILES:
        raise ValueError("CORE_SET_INSTANCE_PROFILE_INVALID")
    profile = instance["profile"]
    return (
        validate_instance(profile, instance)
        if profile in BUSINESS_PROFILES
        else validate_core_instance(profile, instance)
    )


def generate(profile, seed):
    return validate(
        generate_business_instance(profile, seed)
        if profile in BUSINESS_PROFILES
        else generate_core_instance(profile, seed)
    )


def instance_id(instance):
    return f"{instance['profile']}-seed-{instance['seed']}"


def decode(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError("CORE_SET_DUPLICATE_JSON_FIELD")
            result[key] = value
        return result

    def constant(_):
        raise ValueError("CORE_SET_NONFINITE_JSON")

    return json.loads(raw, object_pairs_hook=pairs, parse_constant=constant)


def regular_bytes(path, limit):
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_size > limit:
        raise ValueError("CORE_SET_FILE_INVALID")
    return path.read_bytes()


def seal_instances(directory, instances):
    items = [validate(instance) for instance in instances]
    ids = [instance_id(instance) for instance in items]
    if not 1 <= len(ids) <= 1000 or len(set(ids)) != len(ids):
        raise ValueError("CORE_SET_IDENTITIES_INVALID")
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=False)
    index = {
        "schema": "sujie-core-sealed-development-v1",
        "exposure": "development-exposed",
        "formal_ready": False,
        "instances": [],
    }
    for identifier, instance in zip(ids, items, strict=True):
        raw = encoded(instance).encode("utf-8")
        name = identifier + ".json"
        (directory / name).write_bytes(raw)
        index["instances"].append(
            {"id": identifier, "file": name, "sha256": hashlib.sha256(raw).hexdigest()}
        )
    (directory / "manifest-index.json").write_bytes(encoded(index).encode("utf-8"))
    return index


def load_sealed_instances(directory):
    directory = Path(directory)
    if directory.is_symlink() or not directory.is_dir():
        raise ValueError("CORE_SET_DIRECTORY_INVALID")
    index = decode(regular_bytes(directory / "manifest-index.json", 1024 * 1024))
    if (
        not isinstance(index, dict)
        or set(index) != {"schema", "exposure", "formal_ready", "instances"}
        or index["schema"] != "sujie-core-sealed-development-v1"
        or index["exposure"] != "development-exposed"
        or index["formal_ready"] is not False
        or not isinstance(index["instances"], list)
        or not 1 <= len(index["instances"]) <= 1000
    ):
        raise ValueError("CORE_SET_INDEX_INVALID")
    result = {}
    pattern = "(?:" + "|".join(PROFILES) + r")-seed-(?:0|[1-9][0-9]{0,9})"
    for row in index["instances"]:
        if (
            not isinstance(row, dict)
            or set(row) != {"id", "file", "sha256"}
            or not isinstance(row["id"], str)
            or not re.fullmatch(pattern, row["id"])
            or row["file"] != row["id"] + ".json"
            or row["id"] in result
        ):
            raise ValueError("CORE_SET_INDEX_PATH_INVALID")
        raw = regular_bytes(directory / row["file"], 128 * 1024)
        if hashlib.sha256(raw).hexdigest() != row["sha256"]:
            raise ValueError("CORE_SET_INSTANCE_HASH_MISMATCH")
        instance = validate(decode(raw))
        if instance_id(instance) != row["id"]:
            raise ValueError("CORE_SET_INSTANCE_ID_MISMATCH")
        result[row["id"]] = instance
    if any(not stat.S_ISREG(path.lstat().st_mode) for path in directory.iterdir()) or {
        path.name for path in directory.iterdir()
    } != {"manifest-index.json", *(row["file"] for row in index["instances"])}:
        raise ValueError("CORE_SET_EXTRA_OR_NONREGULAR_FILE")
    return index, result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--profile", choices=PROFILES, action="append")
    parser.add_argument("--seed", type=int, action="append")
    args = parser.parse_args()
    seal_instances(
        args.out_dir,
        [
            generate(profile, seed)
            for profile in (args.profile or PROFILES)
            for seed in (args.seed or [0, 1])
        ],
    )
