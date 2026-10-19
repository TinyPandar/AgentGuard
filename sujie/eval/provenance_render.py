"""Optional Graphviz subprocess renderer for provenance evaluation artifacts."""

import shutil
import subprocess


def render_dot(dot_source: str, fmt: str = "svg") -> bytes | None:
    binary = shutil.which("dot")
    if binary is None:
        return None
    result = subprocess.run(
        [binary, f"-T{fmt}"],
        input=dot_source.encode("utf-8"),
        capture_output=True,
        timeout=60,
        check=True,
    )
    return result.stdout
