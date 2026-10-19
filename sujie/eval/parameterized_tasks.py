"""Deterministic, development-exposed instances; sealing does not create a holdout."""

import argparse
import hashlib
import json
import random
import re
import stat
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "demo-agent"))

from sujie_demo_agent.business_workflows import WORKFLOWS, validate_instance  # noqa: E402

PROFILES = ("event-timeline", "attachment-audit")


def encoded(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n"


def instance_id(profile, seed):
    return f"{profile}-seed-{seed}"


def generate_instance(profile, seed):
    if profile not in PROFILES or type(seed) is not int or not 0 <= seed < 2**32:
        raise ValueError("PARAMETERIZED_SEED_OR_PROFILE_INVALID")
    rng = random.Random(seed)
    paths = WORKFLOWS[profile]["resources"]
    if profile == "event-timeline":
        start = datetime(2026, 1, 1, tzinfo=timezone.utc) + timedelta(
            days=seed % 300, seconds=seed % 10000
        )
        span = 60 + seed % 300

        def stamp(seconds):
            return (start + timedelta(seconds=seconds)).isoformat().replace("+00:00", "Z")

        target = {
            "incident_id": f"INC-{seed}",
            "actor": f"svc-{seed}",
            "session_id": f"session-{seed}",
            "window_start": stamp(0),
            "window_end": stamp(span),
        }

        def event(suffix, seconds, *, actor=None, session=None):
            return {
                "id": f"ev-{seed}-{suffix}",
                "at": stamp(seconds),
                "kind": "login" if suffix.startswith("a") else "exec",
                "actor": actor or target["actor"],
                "session_id": session or target["session_id"],
            }

        auth = [
            event("before", -1),
            event("actor", 0, actor="unrelated"),
            event("session", span, session="unrelated"),
        ]
        process = [event("after", span + 1)]
        if seed % 4:
            # Both inclusive endpoints and a cross-file timestamp tie are deliberate.
            auth += [event("a-start", 0), event("z-tie", span // 2)]
            process += [event("a-tie", span // 2), event("z-end", span)]
        rng.shuffle(auth)
        rng.shuffle(process)
        files = {
            paths[0]: encoded({"events": auth}),
            paths[1]: encoded({"events": process}),
            paths[2]: encoded(
                {"sessions": {target["session_id"]: f"worker-{seed}", "unrelated": "other-worker"}}
            ),
        }
    else:
        mode = seed % 4
        rows = [
            (
                f"sku-{seed}-{index}",
                0 if seed == 0 else rng.randrange(0, 8),
                0 if seed == 0 else rng.choice((1, 99, 100, 19900, 999999999)),
            )
            for index in range(1 + seed % 5)
        ]
        total = sum(quantity * price for _, quantity, price in rows)
        currency = ("CNY", "USD", "EUR", "JPY")[seed % 4]
        claim = total + (1 + seed % 100 if mode == 1 else 0)
        invoice = total + (1 + seed % 100 if mode == 2 else 0)
        target = {
            "mail_id": f"MAIL-{seed}",
            "currency": currency,
            "claimed_total_cents": claim,
            "message": "核查原始邮件、发票和完整明细，按整数分报告差额。",
        }
        files = {
            paths[0]: encoded(
                {
                    "invoice_id": f"INVOICE-{seed}",
                    "currency": "CNY" if mode == 3 else currency,
                    "total_cents": invoice,
                }
            ),
            paths[1]: "sku,quantity,unit_price_cents\n"
            + "".join(f"{sku},{quantity},{price}\n" for sku, quantity, price in rows),
        }
    return validate_instance(
        profile,
        {
            "schema": "sujie-business-instance-development-v1",
            "profile": profile,
            "seed": seed,
            "exposure": "development-exposed",
            "formal_ready": False,
            "target": target,
            "files": files,
        },
    )


def seal_instances(directory, instances):
    """Create a new byte-hashed development manifest set; never overwrite evidence."""
    directory = Path(directory)
    validated = [validate_instance(item["profile"], item) for item in instances]
    names = [instance_id(item["profile"], item["seed"]) for item in validated]
    if len(set(names)) != len(names) or not names:
        raise ValueError("PARAMETERIZED_INSTANCE_SET_INVALID")
    directory.mkdir(parents=True, exist_ok=False)
    index = {
        "schema": "sujie-sealed-development-instances-v1",
        "exposure": "development-exposed",
        "formal_ready": False,
        "instances": [],
    }
    for name, item in zip(names, validated, strict=True):
        raw = encoded(item).encode("utf-8")
        (directory / (name + ".json")).write_bytes(raw)
        index["instances"].append(
            {"id": name, "file": name + ".json", "sha256": hashlib.sha256(raw).hexdigest()}
        )
    (directory / "manifest-index.json").write_text(encoded(index), "utf-8")
    return index


def load_sealed_instances(directory):
    directory = Path(directory)
    if directory.is_symlink() or not directory.is_dir():
        raise ValueError("PARAMETERIZED_INPUT_DIRECTORY_INVALID")

    def read_regular(path, limit):
        if not stat.S_ISREG(path.lstat().st_mode) or path.stat().st_size > limit:
            raise ValueError("PARAMETERIZED_INPUT_FILE_INVALID")
        return path.read_bytes()

    def decode(raw):
        def pairs(items):
            result = {}
            for key, value in items:
                if key in result:
                    raise ValueError("PARAMETERIZED_DUPLICATE_JSON_FIELD")
                result[key] = value
            return result

        def reject_constant(value):
            raise ValueError("PARAMETERIZED_NONFINITE_JSON")

        return json.loads(raw, object_pairs_hook=pairs, parse_constant=reject_constant)

    index = decode(read_regular(directory / "manifest-index.json", 1024 * 1024))
    if (
        not isinstance(index, dict)
        or set(index) != {"schema", "exposure", "formal_ready", "instances"}
        or index["schema"] != "sujie-sealed-development-instances-v1"
        or index["exposure"] != "development-exposed"
        or index["formal_ready"] is not False
        or not isinstance(index["instances"], list)
        or not 1 <= len(index["instances"]) <= 1000
    ):
        raise ValueError("PARAMETERIZED_INDEX_SCOPE_INVALID")
    result = {}
    for row in index["instances"]:
        if (
            not isinstance(row, dict)
            or set(row) != {"id", "file", "sha256"}
            or not isinstance(row["id"], str)
            or not re.fullmatch(
                r"(?:event-timeline|attachment-audit)-seed-(?:0|[1-9][0-9]{0,9})", row["id"]
            )
            or row["file"] != row["id"] + ".json"
            or Path(row["file"]).name != row["file"]
            or row["id"] in result
        ):
            raise ValueError("PARAMETERIZED_INDEX_PATH_INVALID")
        # JSON embeds source text with escaped quotes/newlines; the manifest can
        # be larger than the already-bounded actual MCP input byte total.
        raw = read_regular(directory / row["file"], 128 * 1024)
        if hashlib.sha256(raw).hexdigest() != row["sha256"]:
            raise ValueError("PARAMETERIZED_INSTANCE_HASH_MISMATCH")
        item = decode(raw)
        if not isinstance(item, dict) or "profile" not in item:
            raise ValueError("PARAMETERIZED_INSTANCE_SHAPE_INVALID")
        validated = validate_instance(item["profile"], item)
        if row["id"] != instance_id(item["profile"], item["seed"]):
            raise ValueError("PARAMETERIZED_INSTANCE_ID_MISMATCH")
        result[row["id"]] = validated
    if any(not stat.S_ISREG(path.lstat().st_mode) for path in directory.iterdir()) or {
        path.name for path in directory.iterdir()
    } != {
        "manifest-index.json",
        *(row["file"] for row in index["instances"]),
    }:
        raise ValueError("PARAMETERIZED_INSTANCE_SET_INVALID")
    return index, result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", required=True, type=Path)
    parser.add_argument("--seed", type=int, action="append", dest="seeds")
    args = parser.parse_args()
    seal_instances(
        args.out_dir,
        [
            generate_instance(profile, seed)
            for profile in PROFILES
            for seed in (args.seeds or [0, 1, 2, 3])
        ],
    )
