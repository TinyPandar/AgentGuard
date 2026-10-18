#!/usr/bin/env python3
"""Check report dependencies, references, anonymity and cited source versions.

This is a source check. It does not compile TeX or certify PDF layout/fonts.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re


def main() -> int:
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
    cites = [x.strip() for group in re.findall(r"\\cite\{([^}]+)\}", combined) for x in group.split(",")]
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
    abstract = re.sub(r"\\(?:chapter\*|addcontentsline)\{[^}]*\}(?:\{[^}]*\})*", "", abstract)
    abstract = re.sub(r"\\[A-Za-z]+", "", abstract)
    abstract_length = len(re.sub(r"[\s{}]", "", abstract))
    if abstract_length > 500:
        errors.append(f"Abstract exceeds conservative 500-character budget: {abstract_length}")
    if re.search(r"/Users/|[A-Z]:\\Users\\|jiapengLi11|lijiapeng|队长姓名|TODO|矢量图另附", combined):
        errors.append("Identity/path or unfinished placeholder found in report source")
    instruction = (project / "sections/instructions.tex").read_text()
    if "本页不删除" not in instruction:
        errors.append("Official instruction page is missing")
    if len(re.findall(r"\\chapter\{", combined)) != 5:
        errors.append("Expected five numbered report chapters")
    record = json.loads((repo / "docs/validation/MAIN_SYNC_VALIDATION_2026-10-18.json").read_text())
    mismatches = []
    for name, expected in record["candidate_source_hashes"].items():
        path = repo / name
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected.removeprefix("sha256:"):
            mismatches.append(name)
    if mismatches:
        errors.append(f"Cited integration source version has changed: {mismatches}")
    result = {"ok": not errors, "tex_files": len(visited), "abstract_characters_conservative": abstract_length,
              "references": len(bib), "source_files_checked": len(record["candidate_source_hashes"]),
              "source_mismatches": mismatches, "check_scope": "tex_sources_and_runtime_version", "errors": errors}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return int(bool(errors))


if __name__ == "__main__":
    raise SystemExit(main())
