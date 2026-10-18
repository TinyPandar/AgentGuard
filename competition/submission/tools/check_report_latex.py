#!/usr/bin/env python3
"""Check report dependencies, references, anonymity and cited source versions.

This is a source check. It does not compile TeX or certify PDF layout/fonts.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess


def _repo_path(name: str) -> bool:
    return (
        isinstance(name, str)
        and bool(name)
        and not any(character in name for character in "\\\n\r\0:")
        and not PurePosixPath(name).is_absolute()
        and ".." not in PurePosixPath(name).parts
        and PurePosixPath(name).as_posix() == name
    )


def _git_blobs(repo: Path, commit: str, paths: list[str]) -> dict[str, bytes]:
    """Read exact Git bytes in one process, without checkout newline conversion."""
    try:
        result = subprocess.run(
            ["git", "cat-file", "--batch"],
            cwd=repo,
            input="".join(f"{commit}:{name}\n" for name in paths).encode("utf-8"),
            capture_output=True,
            check=True,
            timeout=30,
        )
    except (OSError, subprocess.SubprocessError) as error:
        raise ValueError(
            "Cited Git snapshot unavailable; fetch its history (CI uses fetch-depth: 0)"
        ) from error
    output, offset, blobs = result.stdout, 0, {}
    for name in paths:
        end = output.find(b"\n", offset)
        header = output[offset:end].split()
        if (
            end < 0
            or len(header) != 3
            or header[1] != b"blob"
            or not header[2].isdigit()
        ):
            raise ValueError(
                f"Cited Git blob unavailable: {name}; fetch the pinned commit history"
            )
        size = int(header[2])
        start = end + 1
        if output[start + size : start + size + 1] != b"\n":
            raise ValueError(f"Invalid Git blob response: {name}")
        blobs[name] = output[start : start + size]
        offset = start + size + 1
    return blobs


def check_runtime(repo: Path, binding: dict, require_current: bool = False) -> dict:
    """Historical evidence stays pinned; current-tree drift is reported separately."""
    commit = binding.get("source_commit", "")
    record_path = binding.get("validation_record", "")
    record_hash = binding.get("validation_record_sha256", "")
    if (
        binding.get("schema") != "sujie-report-source-binding-v1"
        or not isinstance(commit, str)
        or re.fullmatch(r"[a-f0-9]{40}", commit) is None
        or not _repo_path(record_path)
        or not isinstance(record_hash, str)
        or re.fullmatch(r"[a-f0-9]{64}", record_hash) is None
    ):
        raise ValueError("Invalid report source binding")
    raw = _git_blobs(repo, commit, [record_path])[record_path]
    if hashlib.sha256(raw).hexdigest() != record_hash:
        raise ValueError("Cited validation record digest mismatch")
    hashes = json.loads(raw).get("candidate_source_hashes")
    if (
        not isinstance(hashes, dict)
        or not hashes
        or any(
            not _repo_path(name)
            or not isinstance(expected, str)
            or re.fullmatch(r"(?:sha256:)?[a-f0-9]{64}", expected) is None
            for name, expected in hashes.items()
        )
    ):
        raise ValueError("Invalid cited source hash manifest")
    blobs = _git_blobs(repo, commit, list(hashes))
    mismatches, current_mismatches = [], []
    for name, expected in hashes.items():
        expected = expected.removeprefix("sha256:")
        if hashlib.sha256(blobs[name]).hexdigest() != expected:
            mismatches.append(name)
        path = repo / name
        if (
            not path.is_file()
            or hashlib.sha256(path.read_bytes()).hexdigest() != expected
        ):
            current_mismatches.append(name)
    errors = []
    if mismatches:
        errors.append(f"Cited integration source snapshot mismatch: {mismatches}")
    if require_current and current_mismatches:
        errors.append(
            f"Current source differs from the cited report version: {current_mismatches}"
        )
    return {
        "cited_source_commit": commit,
        "validation_record_sha256": record_hash,
        "source_files_checked": len(hashes),
        "source_mismatches": mismatches,
        "current_source_mismatches": current_mismatches,
        "current_source_matches_report": not current_mismatches,
        "current_source_required": require_current,
        "runtime_acceptance_scope": "cited_snapshot_only; current checkout requires separate validation",
        "errors": errors,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--require-current-source",
        action="store_true",
        help="Also reject working-tree changes relative to the report's cited snapshot.",
    )
    args = parser.parse_args()
    submission = Path(__file__).resolve().parents[1]
    project = submission / "latex"
    repo = submission.parents[1]
    errors: list[str] = []
    visited: set[Path] = set()

    def read(path: Path) -> str:
        path = path.resolve()
        if not path.is_relative_to(project.resolve()) or not path.is_file():
            errors.append(f"Missing or external TeX input: {path.name}")
            return ""
        if path in visited:
            errors.append(f"Repeated or cyclic input: {path.name}")
            return ""
        visited.add(path)
        text = path.read_text("utf-8")
        return re.sub(r"\\input\{([^}]+)\}", lambda m: read(project / m[1]), text)

    combined = read(project / "main.tex")
    labels = re.findall(r"\\label\{([^}]+)\}", combined)
    refs = re.findall(r"\\(?:ref|pageref)\{([^}]+)\}", combined)
    bib = re.findall(r"\\bibitem\{([^}]+)\}", combined)
    cites = [
        x.strip()
        for group in re.findall(r"\\cite\{([^}]+)\}", combined)
        for x in group.split(",")
    ]
    for kind, keys in [("label", labels), ("bibitem", bib)]:
        if len(keys) != len(set(keys)):
            errors.append(f"Duplicate {kind}")
    missing = (set(refs) - {"LastPage"} - set(labels)) | (set(cites) - set(bib))
    if missing:
        errors.append(f"Unresolved references: {sorted(missing)}")
    stack: list[str] = []
    for kind, env in re.findall(r"\\(begin|end)\{([^}]+)\}", combined):
        if kind == "begin":
            stack.append(env)
        elif not stack or stack.pop() != env:
            errors.append(f"Unbalanced environment: {env}")
    if stack:
        errors.append(f"Unclosed environments: {stack}")
    abstract = (project / "sections/abstract.tex").read_text().split(r"\noindent")[0]
    abstract = re.sub(
        r"\\(?:chapter\*|addcontentsline)\{[^}]*\}(?:\{[^}]*\})*", "", abstract
    )
    abstract = re.sub(r"\\[A-Za-z]+", "", abstract)
    abstract_length = len(re.sub(r"[\s{}]", "", abstract))
    if abstract_length > 500:
        errors.append(
            f"Abstract exceeds conservative 500-character budget: {abstract_length}"
        )
    if re.search(
        r"/Users/|[A-Z]:\\Users\\|jiapengLi11|lijiapeng|队长姓名|TODO|矢量图另附",
        combined,
    ):
        errors.append("Identity/path or unfinished placeholder found in report source")
    instruction = (project / "sections/instructions.tex").read_text()
    if "本页不删除" not in instruction:
        errors.append("Official instruction page is missing")
    if len(re.findall(r"\\chapter\{", combined)) != 5:
        errors.append("Expected five numbered report chapters")
    runtime = {}
    try:
        binding = json.loads((project / "runtime-version.json").read_text("utf-8"))
        runtime = check_runtime(repo, binding, args.require_current_source)
        errors.extend(runtime.pop("errors"))
        if binding["source_commit"][:7] not in combined:
            errors.append("Report text must identify its cited source commit")
    except (OSError, ValueError, TypeError, AttributeError) as error:
        errors.append(f"Runtime version check failed: {error}")
    result = {
        "ok": not errors,
        "tex_files": len(visited),
        "abstract_characters_conservative": abstract_length,
        "references": len(bib),
        **runtime,
        "check_scope": "tex_sources_and_cited_runtime_snapshot",
        "errors": errors,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if summary_path := os.environ.get("GITHUB_STEP_SUMMARY"):
        summary = (
            "### 报告源码版本校验\n\n"
            f"- 结果：{'通过' if not errors else '失败'}\n"
            f"- 报告固定提交：`{runtime.get('cited_source_commit', 'unavailable')}`\n"
            f"- 校验源码：{runtime.get('source_files_checked', 0)} 份\n"
            f"- 当前工作区差异：{len(runtime.get('current_source_mismatches', []))} 份\n\n"
            "本任务验证报告所引用的历史版本及PDF构建。当前程序的验收另见质量检查；"
            "报告通过不表示新控制台已纳入该历史验收。\n"
        )
        with Path(summary_path).open("a", encoding="utf-8") as stream:
            stream.write(summary)
    return int(bool(errors))


if __name__ == "__main__":
    raise SystemExit(main())
