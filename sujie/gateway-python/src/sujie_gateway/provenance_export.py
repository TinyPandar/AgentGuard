"""Exporters for the provenance graph: Mermaid, Graphviz DOT/SVG, timeline SVG, HTML.

All exporters are pure functions of the (already redacted) graph and produce
byte-identical output for identical graphs. Graphviz is optional: when the
``dot`` binary is missing, the bundle still contains Mermaid sources, the
pure-Python timeline SVG and a self-contained HTML report.
"""

from __future__ import annotations

import html
import shutil
import subprocess
from pathlib import Path

from .provenance_graph import ProvenanceGraph, stable_json

COLORS = {
    "source": ("#dbeafe", "#1d4ed8"),
    "content": ("#f8fafc", "#475569"),
    "span": ("#fee2e2", "#b91c1c"),
    "agent": ("#dcfce7", "#15803d"),
    "gateway": ("#ede9fe", "#6d28d9"),
    "mcp_server": ("#ccfbf1", "#0f766e"),
    "tool_call": ("#f1f5f9", "#334155"),
    "decision": ("#fef9c3", "#a16207"),
    "impact": ("#fff7ed", "#c2410c"),
}
DECISION_COLORS = {
    "ALLOW": ("#dcfce7", "#15803d"),
    "ASK": ("#fef3c7", "#b45309"),
    "BLOCK": ("#fee2e2", "#b91c1c"),
}
IMPACT_COLORS = {
    "affected": ("#ffedd5", "#c2410c"),
    "pending": ("#fef3c7", "#b45309"),
    "prevented": ("#e2e8f0", "#475569"),
}
SOURCE_TAG = {"user": "USER", "external": "EXTERNAL", "memory": "MEMORY"}


def _short(text: str, limit: int) -> str:
    text = " ".join(str(text).split())
    return text if len(text) <= limit else text[: limit - 1] + "…"


def node_lines(graph: ProvenanceGraph, node_id: str) -> list[str]:
    node = graph.nodes[node_id]
    a = node.attrs
    if node.type == "source":
        return [
            f"[{SOURCE_TAG.get(a['kind'], a['kind'].upper())}] {node.label}",
            _short(a.get("preview") or a["locator"], 48),
        ]
    if node.type == "content":
        flags = [a["confidentiality"]]
        if a["findings"]:
            flags.append("INJECTION-FLAGGED")
        return [f"{node.id} {a['origin_type']}", _short(a["source_id"], 46), " · ".join(flags)]
    if node.type == "span":
        return [
            f"payload chars {a['char_start']}-{a['char_end']}",
            f"tokens {a['token_start']}-{a['token_end']} ({a['precision']})",
            "“" + _short(a["excerpt"], 44) + "”",
        ]
    if node.type == "agent":
        role = "main agent" if a["role"] == "main" else f"sub-agent depth {a['depth']}"
        return [node.label, role]
    if node.type == "gateway":
        return [node.label]
    if node.type == "mcp_server":
        return [node.label, a.get("server_name", "")]
    if node.type == "tool_call":
        agent = graph.nodes[a["agent"]].label
        params = a["params"] if isinstance(a["params"], dict) else {}
        lines = [f"{agent} → {a['tool']}"]
        for key, value in list(params.items())[:2]:
            lines.append(_short(f"{key}={value}", 52))
        return lines
    if node.type == "decision":
        return [
            f"{a['decision']} {a['reason']}",
            f"rule {_short(a['rule'], 40)}",
            f"risk {a['provenance_risk']['level']} (runtime {a['runtime_risk']})",
        ]
    if node.type == "impact":
        return [
            f"[{a['category']}]",
            _short(a["resource"], 48),
            f"{a['status']} ({', '.join(a['kinds'])})",
        ]
    return [node.label]


def _style(graph: ProvenanceGraph, node_id: str) -> tuple[str, str]:
    node = graph.nodes[node_id]
    if node.type == "decision":
        return DECISION_COLORS.get(node.attrs["decision"], COLORS["decision"])
    if node.type == "impact":
        return IMPACT_COLORS.get(node.attrs["status"], COLORS["impact"])
    return COLORS[node.type]


def _visible(graph: ProvenanceGraph, path_only: bool) -> list[str]:
    ids = list(graph.nodes)
    if path_only and graph.attack_path:
        keep = set(graph.attack_path)
        ids = [n for n in ids if n in keep]
    # The gateway evaluates every decision; it is drawn as the timeline lane instead.
    return [
        n
        for n in ids
        if not graph.nodes[n].attrs.get("trusted_probe") and graph.nodes[n].type != "gateway"
    ]


# ---------------------------------------------------------------------------
# Mermaid


def _mm_text(text: str) -> str:
    """Mermaid label text: escape entity-sensitive characters with #code; entities."""
    out = []
    for char in text:
        if char in '"#;<>&`[]{}|':
            out.append(f"#{ord(char)};")
        else:
            out.append(char)
    return "".join(out)


SHAPES = {
    "source": ("([", "])"),
    "content": ("[", "]"),
    "span": ("[[", "]]"),
    "agent": ("{{", "}}"),
    "gateway": ("[/", "/]"),
    "mcp_server": ("[(", ")]"),
    "tool_call": ("(", ")"),
    "decision": ("{", "}"),
    "impact": (">", "]"),
}


def to_mermaid_flowchart(graph: ProvenanceGraph, *, path_only: bool = False) -> str:
    ids = _visible(graph, path_only)
    alias = {node_id: f"n{index}" for index, node_id in enumerate(ids)}
    lines = ["flowchart LR"]
    for node_id in ids:
        node = graph.nodes[node_id]
        left, right = SHAPES[node.type]
        label = "<br/>".join(_mm_text(line) for line in node_lines(graph, node_id))
        lines.append(f'    {alias[node_id]}{left}"{label}"{right}')
    path = set(graph.attack_path)
    link_index = 0
    red_links = []
    for edge in graph.edges:
        if edge.src not in alias or edge.dst not in alias:
            continue
        arrow = "-.->" if edge.type in {"ROUTED_TO"} and not edge.attrs.get("executed") else "-->"
        if edge.type == "PREVENTED_EFFECT":
            arrow = "-.-x"
        lines.append(f"    {alias[edge.src]} {arrow}|{edge.type}| {alias[edge.dst]}")
        if edge.src in path and edge.dst in path and edge.type not in {"EVALUATES"}:
            red_links.append(str(link_index))
        link_index += 1
    for kind, (fill, stroke) in COLORS.items():
        lines.append(f"    classDef {kind} fill:{fill},stroke:{stroke},color:#0f172a")
    lines.append("    classDef block fill:#fee2e2,stroke:#b91c1c,stroke-width:3px,color:#7f1d1d")
    lines.append("    classDef allow fill:#dcfce7,stroke:#15803d,color:#14532d")
    lines.append("    classDef ask fill:#fef3c7,stroke:#b45309,color:#78350f")
    for node_id in ids:
        node = graph.nodes[node_id]
        cls = node.type
        if node.type == "decision":
            cls = {"BLOCK": "block", "ALLOW": "allow", "ASK": "ask"}[node.attrs["decision"]]
        lines.append(f"    class {alias[node_id]} {cls}")
    if red_links:
        lines.append(f"    linkStyle {','.join(red_links)} stroke:#dc2626,stroke-width:3px")
    return "\n".join(lines) + "\n"


def to_mermaid_sequence(graph: ProvenanceGraph) -> str:
    alias = {lane["id"]: f"L{index}" for index, lane in enumerate(graph.lanes)}
    lines = ["sequenceDiagram", "    autonumber"]
    for lane in graph.lanes:
        kind = "actor" if lane["id"] == "user" else "participant"
        lines.append(f"    {kind} {alias[lane['id']]} as {_mm_text(lane['label'])}")
    for step in graph.timeline:
        src, dst = alias.get(step["from"]), alias.get(step["to"])
        if src is None or dst is None:
            continue
        text = _mm_text(_short(step["text"], 110))
        if step["kind"] == "note":
            prefix = "⚠ " if step.get("alert") else ""
            lines.append(f"    Note over {src}: {prefix}{text}")
        elif step["kind"] == "deny":
            lines.append(f"    {src}--x{dst}: {text}")
        elif step["kind"] == "reply":
            lines.append(f"    {src}-->>{dst}: {text}")
        elif step["kind"] == "spawn":
            lines.append(f"    {src}-)+{dst}: {text}")
        else:
            lines.append(f"    {src}->>{dst}: {text}")
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# Graphviz


def _dot_str(text: str) -> str:
    return '"' + text.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n") + '"'


def to_dot(graph: ProvenanceGraph, *, path_only: bool = False) -> str:
    ids = _visible(graph, path_only)
    keep = set(ids)
    path = set(graph.attack_path)
    out = [
        "digraph provenance {",
        f'  graph [rankdir={"TB" if path_only else "LR"}, fontname="Helvetica", fontsize=11, nodesep=0.35, ranksep=0.6,'
        ' bgcolor="white", labelloc=t, label='
        + _dot_str("Attack-path DAG (red = reconstructed path of the focused decision)")
        + "];",
        '  node [fontname="Helvetica", fontsize=10, style="rounded,filled", shape=box];',
        '  edge [fontname="Helvetica", fontsize=8, color="#94a3b8", fontcolor="#64748b"];',
    ]
    shapes = {
        "source": "ellipse",
        "agent": "hexagon",
        "decision": "diamond",
        "mcp_server": "cylinder",
        "impact": "folder",
        "span": "note",
        "gateway": "parallelogram",
        "tool_call": "box",
        "content": "box",
    }

    def emit(node_id: str, indent: str = "  ") -> None:
        fill, stroke = _style(graph, node_id)
        node = graph.nodes[node_id]
        width = "3" if node_id in path else "1.2"
        out.append(
            f"{indent}{_dot_str(node_id)} [label={_dot_str(chr(10).join(node_lines(graph, node_id)))}"
            f", shape={shapes[node.type]}, fillcolor={_dot_str(fill)}, color={_dot_str(stroke)}"
            f", penwidth={width}];"
        )

    agents = [n for n in ids if graph.nodes[n].type == "agent"]
    placed: set[str] = set()
    for agent in agents:
        members = [agent] + [
            n
            for n in ids
            if graph.nodes[n].type == "tool_call" and graph.nodes[n].attrs["agent"] == agent
        ]
        members += [
            e.dst
            for e in graph.edges
            if e.type == "DECIDED_BY" and e.src in members and e.dst in keep
        ]
        out.append(f"  subgraph {_dot_str('cluster_' + agent)} {{")
        out.append(
            f"    label={_dot_str(graph.nodes[agent].label + ' lane')};"
            ' style="rounded,dashed"; color="#86efac"; fontcolor="#15803d";'
        )
        for member in members:
            if member not in placed:
                emit(member, "    ")
                placed.add(member)
        out.append("  }")
    groups = {"mcp_server": "MCP servers (via StdioMCPProxy)", "impact": "Impact scope"}
    for kind, label in groups.items():
        members = [n for n in ids if graph.nodes[n].type == kind and n not in placed]
        if not members:
            continue
        out.append(f"  subgraph {_dot_str('cluster_' + kind)} {{")
        out.append(f'    label={_dot_str(label)}; style="rounded,dashed"; color="#cbd5e1";')
        for member in members:
            emit(member, "    ")
            placed.add(member)
        out.append("  }")
    for node_id in ids:
        if node_id not in placed:
            emit(node_id)
    for edge in graph.edges:
        if edge.src not in keep or edge.dst not in keep or edge.type == "EVALUATES":
            continue
        on_path = edge.src in path and edge.dst in path and edge.type != "EVALUATES"
        attrs = [f"label={_dot_str(edge.type)}"]
        if on_path:
            attrs += ['color="#dc2626"', "penwidth=2.4", 'fontcolor="#b91c1c"']
        if edge.type == "PREVENTED_EFFECT" or (
            edge.type == "ROUTED_TO" and not edge.attrs.get("executed")
        ):
            attrs.append("style=dashed")
        if edge.type == "ROUTED_TO":
            attrs.append("weight=0")
        out.append(f"  {_dot_str(edge.src)} -> {_dot_str(edge.dst)} [{', '.join(attrs)}];")
    out.append("}")
    return "\n".join(out) + "\n"


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


# ---------------------------------------------------------------------------
# Timeline SVG (pure Python swimlanes)


def timeline_svg(graph: ProvenanceGraph) -> str:
    lane_w, left, top, row = 190, 64, 72, 30
    lanes = graph.lanes
    x = {lane["id"]: left + lane_w * i + lane_w // 2 for i, lane in enumerate(lanes)}
    steps = [s for s in graph.timeline if s["from"] in x and s["to"] in x]
    width = left + lane_w * len(lanes) + 20
    height = top + row * (len(steps) + 1) + 20
    esc = html.escape
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" font-family="Helvetica, Arial, sans-serif" font-size="11">',
        "<defs>",
        '<marker id="ar" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7"'
        ' orient="auto"><path d="M0 0L10 5L0 10z" fill="#334155"/></marker>',
        '<marker id="arr" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7"'
        ' orient="auto"><path d="M0 0L10 5L0 10z" fill="#dc2626"/></marker>',
        '<marker id="arg" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7"'
        ' orient="auto"><path d="M0 0L10 5L0 10z" fill="#15803d"/></marker>',
        "</defs>",
        f'<rect width="{width}" height="{height}" fill="white"/>',
        f'<text x="12" y="20" font-size="14" font-weight="bold" fill="#0f172a">'
        f"{esc('Timeline (swimlanes): user / agents / gateway / MCP servers')}</text>",
    ]
    for lane in lanes:
        cx = x[lane["id"]]
        kind = (
            "#dbeafe"
            if lane["id"] == "user"
            else "#ede9fe"
            if lane["id"] == "gw"
            else "#ccfbf1"
            if lane["id"].startswith("mcp:")
            else "#dcfce7"
        )
        parts.append(
            f'<rect x="{cx - 84}" y="32" width="168" height="26" rx="6" fill="{kind}"'
            ' stroke="#64748b"/>'
        )
        parts.append(
            f'<text x="{cx}" y="49" text-anchor="middle" font-weight="bold">'
            f"{esc(_short(lane['label'], 26))}</text>"
        )
        parts.append(
            f'<line x1="{cx}" y1="58" x2="{cx}" y2="{height - 10}" stroke="#cbd5e1"'
            ' stroke-dasharray="4 4"/>'
        )
    focus_nodes = set(graph.attack_path)
    for index, step in enumerate(steps):
        y = top + row * index + 14
        marker_text = "goal" if step["seq"] < 0 else f"#{step['seq']}"
        parts.append(f'<text x="8" y="{y + 4}" fill="#94a3b8">{marker_text}</text>')
        x1, x2 = x[step["from"]], x[step["to"]]
        text = step["text"]
        if step["kind"] == "note":
            fill, stroke = (
                ("#fee2e2", "#dc2626")
                if step.get("alert")
                else (
                    {
                        "BLOCK": ("#fee2e2", "#b91c1c"),
                        "ALLOW": ("#dcfce7", "#15803d"),
                        "ASK": ("#fef3c7", "#b45309"),
                    }.get(step.get("decision"), ("#f8fafc", "#94a3b8"))
                )
            )
            w = min(lane_w * 2 - 10, max(140, int(len(text) * 6.1) + 16))
            parts.append(
                f'<rect x="{x1 - w // 2}" y="{y - 11}" width="{w}" height="20" rx="4"'
                f' fill="{fill}" stroke="{stroke}"/>'
            )
            parts.append(
                f'<text x="{x1}" y="{y + 3}" text-anchor="middle">'
                f"{esc(_short(text, int(w / 6.1)))}</text>"
            )
            continue
        deny = step["kind"] == "deny"
        spawn = step["kind"] == "spawn"
        color = "#dc2626" if deny else "#15803d" if spawn else "#334155"
        marker = "arr" if deny else "arg" if spawn else "ar"
        dash = ' stroke-dasharray="5 3"' if step["kind"] == "reply" or deny else ""
        bold = step.get("node") in focus_nodes
        stroke_w = 2.4 if bold or deny else 1.3
        direction = 1 if x2 >= x1 else -1
        parts.append(
            f'<line x1="{x1}" y1="{y + 4}" x2="{x2 - 4 * direction}" y2="{y + 4}"'
            f' stroke="{color}" stroke-width="{stroke_w}"{dash} marker-end="url(#{marker})"/>'
        )
        span = max(abs(x2 - x1), lane_w * 2)
        label = _short(text, int(span / 6.0))
        parts.append(
            f'<text x="{(x1 + x2) / 2:.0f}" y="{y - 1}" text-anchor="middle"'
            f' fill="{color}" stroke="white" stroke-width="3" paint-order="stroke">'
            f"{esc(label)}</text>"
        )
    parts.append("</svg>")
    return "\n".join(parts) + "\n"


# ---------------------------------------------------------------------------
# Reports


def _strip_xml(svg: str) -> str:
    start = svg.find("<svg")
    return svg[start:] if start >= 0 else svg


def path_narrative(graph: ProvenanceGraph) -> list[str]:
    lines = []
    for node_id in graph.attack_path:
        node = graph.nodes[node_id]
        if node.type in {"gateway"}:
            continue
        lines.append(f"`{node_id}` **{node.type}** — " + " / ".join(node_lines(graph, node_id)))
    return lines


def to_markdown(graph: ProvenanceGraph, title: str) -> str:
    s = graph.summary
    focus = s.get("focus", {})
    md = [f"# {title}", ""]
    md += [
        "Generated by `sujie_gateway.provenance_export` from a real M1Gateway trace. "
        "All arguments and excerpts are redacted (keys/tokens masked with a hash).",
        "",
        "## Verdict",
        "",
        f"- Decision: **{focus.get('decision')} {focus.get('reason')}** (rule `{focus.get('rule')}`)",
        f"- Provenance risk: **{focus.get('risk', {}).get('level')}** — "
        + "; ".join(focus.get("risk", {}).get("factors", [])),
        f"- Explanation: {focus.get('explanation')}",
        "",
        "## Chain",
        "",
        "- Trigger sources: "
        + ", ".join(f"{t['kind']} `{t['locator']}`" for t in s.get("trigger_sources", [])),
        "- Agent chain: "
        + " → ".join(f"{a['label']} (depth {a['depth']})" for a in s.get("agent_chain", [])),
        "- MCP servers on the path: " + ", ".join(s.get("mcp_servers", [])),
        "",
        "### Payload location (token level)",
        "",
        "| span | chars | bytes | tokens | precision | excerpt (redacted) |",
        "|---|---|---|---|---|---|",
    ]
    for span in s.get("payload_spans", []):
        md.append(
            f"| `{span['id']}` | {span['char_start']}–{span['char_end']} | "
            f"{span['byte_start']}–{span['byte_end']} | {span['token_start']}–{span['token_end']} | "
            f"{span['precision']} | {span['excerpt'].replace('|', '¦')} |"
        )
    md += ["", "### Impact scope", ""]
    for category, items in s.get("impact_scope", {}).items():
        md.append(f"- **{category}**: " + (", ".join(f"`{i}`" for i in items) or "—"))
    md += [
        "",
        "### Tool calls (params redacted, hash kept)",
        "",
        "| # | agent | tool | params | decision | result |",
        "|---|---|---|---|---|---|",
    ]
    for node in sorted(graph.of_type("tool_call"), key=lambda n: n.seq):
        if node.attrs.get("trusted_probe"):
            continue
        decision = next(
            (
                graph.nodes[e.dst]
                for e in graph.edges
                if e.src == node.id and e.type == "DECIDED_BY"
            ),
            None,
        )
        params = ", ".join(f"{k}={v}" for k, v in node.attrs["params"].items())
        result = node.attrs["result"]
        res = ("ok · " + _short(result["preview"], 60)) if result["ok"] else (result["code"] or "—")
        md.append(
            f"| {node.seq} | {graph.nodes[node.attrs['agent']].label} | `{node.attrs['tool']}` | "
            f"{_short(params, 120).replace('|', '¦')} | "
            f"{decision.attrs['decision'] + ' ' + decision.attrs['reason'] if decision else '—'} | "
            f"{res.replace('|', '¦')} |"
        )
    md += [
        "",
        "## 简化版攻击路径（中文，答辩/报告用）",
        "",
        "![简化版攻击路径](attack_path_simple_zh.png)",
        "",
        "```mermaid",
        to_simple_mermaid_zh(graph).rstrip() if graph.focus else "flowchart TB",
        "```",
        "",
        "## Attack-path DAG",
        "",
        "```mermaid",
        to_mermaid_flowchart(graph, path_only=True).rstrip(),
        "```",
        "",
        "## Timeline",
        "",
        "```mermaid",
        to_mermaid_sequence(graph).rstrip(),
        "```",
        "",
        "## Path nodes",
        "",
    ]
    md += [f"{i + 1}. {line}" for i, line in enumerate(path_narrative(graph))]
    return "\n".join(md) + "\n"


def to_html(graph: ProvenanceGraph, title: str, dag_svg: str | None) -> str:
    esc = html.escape
    s = graph.summary
    focus = s.get("focus", {})
    rows = []
    for node in sorted(graph.of_type("tool_call"), key=lambda n: n.seq):
        if node.attrs.get("trusted_probe"):
            continue
        decision = next(
            (
                graph.nodes[e.dst]
                for e in graph.edges
                if e.src == node.id and e.type == "DECIDED_BY"
            ),
            None,
        )
        params = "<br>".join(
            f"<code>{esc(str(k))}</code>={esc(str(v))}" for k, v in node.attrs["params"].items()
        )
        cls = decision.attrs["decision"].lower() if decision else ""
        rows.append(
            f"<tr class='{'path' if node.id in graph.attack_path else ''}'><td>{node.seq}</td>"
            f"<td>{esc(graph.nodes[node.attrs['agent']].label)}</td>"
            f"<td><code>{esc(node.attrs['tool'])}</code></td><td>{params}"
            f"<div class='hash'>{esc(str(node.attrs['arguments_hash'] or ''))}</div></td>"
            f"<td class='{cls}'>{esc(decision.attrs['decision'] + ' ' + decision.attrs['reason']) if decision else '—'}"
            f"<div class='hash'>{esc(decision.attrs['explanation']) if decision else ''}</div></td>"
            f"<td>{esc(node.attrs['result']['code'] or ('ok' if node.attrs['result']['ok'] else ''))}"
            f"<div class='hash'>{esc(_short(node.attrs['result']['preview'], 90))}</div></td></tr>"
        )
    spans = "".join(
        f"<tr><td><code>{esc(x['id'])}</code></td><td>{x['char_start']}–{x['char_end']}</td>"
        f"<td>{x['byte_start']}–{x['byte_end']}</td><td>{x['token_start']}–{x['token_end']}</td>"
        f"<td>{esc(x['precision'])}</td><td class='payload'>{esc(x['excerpt'])}</td></tr>"
        for x in s.get("payload_spans", [])
    )
    impacts = "".join(
        f"<li><b>{esc(category)}</b>: {esc(', '.join(items) or '—')}</li>"
        for category, items in s.get("impact_scope", {}).items()
    )
    chain = " → ".join(esc(f"{a['label']} (depth {a['depth']})") for a in s.get("agent_chain", []))
    sources = ", ".join(esc(f"{t['kind']}: {t['locator']}") for t in s.get("trigger_sources", []))
    dag = (
        _strip_xml(dag_svg)
        if dag_svg
        else "<p>Graphviz not installed; Mermaid source:</p><pre>"
        + esc(to_mermaid_flowchart(graph, path_only=True))
        + "</pre>"
    )
    narrative = "".join(
        f"<li>{esc(line.replace('`', '').replace('**', ''))}</li>" for line in path_narrative(graph)
    )
    return f"""<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><title>{esc(title)}</title>
<style>
body{{font-family:Helvetica,Arial,"PingFang SC","Microsoft YaHei",sans-serif;margin:24px;color:#0f172a;background:#f8fafc}}
h1{{font-size:22px}} h2{{font-size:17px;margin-top:28px}}
.card{{background:white;border:1px solid #e2e8f0;border-radius:10px;padding:14px 18px;margin:12px 0}}
.verdict{{border-left:6px solid #dc2626}}
.scroll{{overflow:auto;background:white;border:1px solid #e2e8f0;border-radius:10px;padding:8px}}
table{{border-collapse:collapse;width:100%;background:white;font-size:12px}}
td,th{{border:1px solid #e2e8f0;padding:6px;vertical-align:top;text-align:left}}
tr.path td{{background:#fff1f2}} td.block{{color:#b91c1c;font-weight:bold}}
td.allow{{color:#15803d;font-weight:bold}} td.ask{{color:#b45309;font-weight:bold}}
.hash{{color:#64748b;font-size:11px;word-break:break-all}} .payload{{color:#b91c1c}}
code{{background:#f1f5f9;padding:1px 4px;border-radius:4px}}
</style></head><body>
<h1>{esc(title)}</h1>
<div class="card verdict"><b>{esc(str(focus.get("decision")))} {esc(str(focus.get("reason")))}</b>
 · rule <code>{esc(str(focus.get("rule")))}</code> · provenance risk
 <b>{esc(str(focus.get("risk", {}).get("level")))}</b><br>{esc(str(focus.get("explanation")))}
<br><span class="hash">{esc("; ".join(focus.get("risk", {}).get("factors", [])))}</span></div>
<div class="card"><b>Trigger sources:</b> {sources}<br><b>Agent chain:</b> {chain}<br>
<b>MCP servers on path:</b> {esc(", ".join(s.get("mcp_servers", [])))}</div>
<h2>Attack-path DAG</h2><div class="scroll">{dag}</div>
<h2>Timeline (swimlanes)</h2><div class="scroll">{_strip_xml(timeline_svg(graph))}</div>
<h2>Payload location (token level)</h2>
<table><tr><th>span</th><th>chars</th><th>bytes</th><th>tokens</th><th>precision</th><th>excerpt (redacted)</th></tr>{spans}</table>
<h2>Impact scope</h2><div class="card"><ul>{impacts}</ul></div>
<h2>Tool calls</h2>
<table><tr><th>#</th><th>agent</th><th>tool</th><th>params (redacted) + hash</th><th>decision</th><th>result</th></tr>{"".join(rows)}</table>
<h2>Path nodes</h2><ol>{narrative}</ol>
</body></html>
"""


def write_bundle(graph: ProvenanceGraph, out_dir: Path, *, title: str) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    files: dict[str, str | bytes] = {
        "graph.json": stable_json(graph),
        "attack_path.mmd": to_mermaid_flowchart(graph, path_only=True),
        "full_graph.mmd": to_mermaid_flowchart(graph),
        "attack_path.dot": to_dot(graph, path_only=True),
        "full_graph.dot": to_dot(graph),
        "timeline.mmd": to_mermaid_sequence(graph),
        "timeline.svg": timeline_svg(graph),
        "README.md": to_markdown(graph, title),
    }
    dag_svg = None
    rendered = render_dot(files["attack_path.dot"], "svg")
    if rendered is not None:
        dag_svg = rendered.decode("utf-8")
        files["attack_path.svg"] = dag_svg
        full = render_dot(files["full_graph.dot"], "svg")
        if full is not None:
            files["full_graph.svg"] = full.decode("utf-8")
    files["report.html"] = to_html(graph, title, dag_svg)
    written = list(export_simple_attack_path_zh(graph, out_dir)) if graph.focus else []
    for name, data in files.items():
        path = out_dir / name
        if isinstance(data, bytes):
            path.write_bytes(data)
        else:
            path.write_text(data, "utf-8")
        written.append(path)
    return written


# ---------------------------------------------------------------------------
# Simplified Chinese attack path (defence slides / competition report)

ZH_FONT = "Noto Sans CJK SC"
ZH_STYLES = {
    "normal": ("#eef2f7", "#475569", "#1e293b"),
    "agent": ("#e0ecff", "#2563eb", "#1e3a8a"),
    "inject": ("#fde2e2", "#dc2626", "#7f1d1d"),
    "sensitive": ("#ffedd5", "#ea580c", "#7c2d12"),
    "block": ("#7f1d1d", "#450a0a", "#ffffff"),
    "result": ("#ecfdf5", "#059669", "#064e3b"),
}
ZH_REASONS = {
    "untrusted_text_directs_agent_action": "指使 Agent 执行操作",
    "untrusted_text_directs_sensitive_exfiltration": "要求读取并外发私钥等敏感数据",
    "untrusted_text_requests_instruction_override": "要求忽略原有指令",
    "untrusted_text_requests_sensitive_effect": "要求外发凭据",
    "untrusted_text_claims_authority": "伪造授权",
    "untrusted_text_requests_prompt_or_secret_disclosure": "索取系统提示或秘密",
}
ZH_FAMILY = {
    "TOOL_POISONING": "工具投毒",
    "CONTEXT_HIJACK": "上下文劫持",
    "AUTHORIZATION_FORGERY": "伪造授权",
    "DATA_EXFILTRATION": "数据外泄",
    "ROLE_SPOOFING": "角色伪装",
    "CHARACTER_ENCODING": "编码绕过",
}
ZH_BLOCK_REASON = {
    "RESOURCE_OUT_OF_SCOPE": "目标不在授权白名单",
    "PROVENANCE_FORBIDS_TRANSFER": "溯源禁止外传",
    "EGRESS_SOURCE_UNREGISTERED": "外发内容来源未登记",
    "EFFECT_NOT_GRANTED": "未授予该类操作",
    "CONTRACT_FORBIDS_EFFECT": "任务契约禁止该操作",
    "SENSITIVE_TARGET_FORBIDDEN": "敏感路径硬阻断",
}


def _host(url: str) -> str:
    from urllib.parse import urlsplit

    try:
        return urlsplit(str(url)).hostname or str(url)
    except ValueError:
        return str(url)


def _wrap(text: str, width: int = 26) -> list[str]:
    """Wrap by display width (CJK = 2) without splitting ASCII words."""
    import re

    lines, current, size = [], "", 0
    for piece in re.findall(r"[A-Za-z0-9_.:/#~-]+|.", text):
        step = sum(1 if ord(c) < 128 else 2 for c in piece)
        if size + step > width * 2 and current.strip():
            lines.append(current.rstrip())
            current, size = "", 0
            if piece == " ":
                continue
        current += piece
        size += step
    if current.strip():
        lines.append(current.rstrip())
    return lines


def simple_attack_path_zh(graph: ProvenanceGraph) -> dict:
    """Five-step Chinese summary of the focused attack path, derived from the graph."""
    if not graph.focus:
        raise ValueError("NO_FOCUS_DECISION")
    nodes, path = graph.nodes, set(graph.attack_path)

    def out(src: str, kind: str) -> list[str]:
        return [e.dst for e in graph.edges if e.src == src and e.type == kind]

    def into(dst: str, kind: str) -> list[str]:
        return [e.src for e in graph.edges if e.dst == dst and e.type == kind]

    focus = nodes[graph.focus]
    focus_call = nodes[into(focus.id, "DECIDED_BY")[0]]
    steps = []
    # 1 user task
    goal = next(
        (
            n
            for n in nodes.values()
            if n.type == "source" and n.attrs["kind"] == "user" and n.id in path
        ),
        None,
    )
    goal_text = goal.attrs.get("preview") or goal.attrs["locator"] if goal else "（无）"
    steps.append({"no": "①", "title": "用户任务", "style": "normal", "lines": _wrap(goal_text)})
    # 2 agent chain
    agents = sorted(
        (n for n in nodes.values() if n.type == "agent" and n.id in path),
        key=lambda n: n.attrs["depth"],
    )
    names = [
        n.label
        if n.attrs["depth"] == 0 and n.attrs["role"] == "main"
        else f"{n.label}（第{n.attrs['depth']}层）"
        for n in agents
    ]
    if agents and agents[0].attrs["role"] == "main":
        names[0] = f"主 Agent（{agents[0].label}）"
    lines = [names[0], *("→ " + name for name in names[1:])]
    budgets = [n.attrs.get("budgets") or {} for n in agents]
    if all(budgets):
        for key, label in (("tool_calls", "工具调用预算"), ("subagents", "子 Agent 名额")):
            if all(key in b for b in budgets):
                lines.append(f"{label}：" + " → ".join(str(b[key]) for b in budgets))
    effects = [set(n.attrs.get("effects") or []) for n in agents]
    removed = sorted(effects[0] - effects[-1]) if len(effects) > 1 else []
    if removed:
        lines.append(f"权限逐级收窄：第{agents[-1].attrs['depth']}层去掉 " + "、".join(removed))
    steps.append({"no": "②", "title": "Agent 委派链", "style": "agent", "lines": lines})
    # 3 injection source
    spans = sorted(
        (n for n in nodes.values() if n.type == "span" and n.id in path),
        key=lambda n: n.attrs["char_start"],
    )
    content = nodes[into(spans[0].id, "CONTAINS")[0]] if spans else None
    if content is not None:
        producer = into(content.id, "RETURNS")
        server = nodes[producer[0]].attrs["mcp_server"] if producer else "?"
        family = content.attrs["findings"][0]["attack_family"] if content.attrs["findings"] else ""
        reasons = []
        for span in spans:
            for reason in span.attrs["reasons"]:
                text = ZH_REASONS.get(reason, reason)
                if text not in reasons:
                    reasons.append(text)
        lines = [
            f"{server} MCP 返回：{content.attrs['source_id'].split(':', 1)[-1]}",
            f"检测到注入：{ZH_FAMILY.get(family, family)}",
        ]
        lines.append(
            "载荷位置："
            + "、".join(f"字符 {s.attrs['char_start']}–{s.attrs['char_end']}" for s in spans)
        )
        lines += _wrap("含义：" + "；".join(reasons))
        steps.append({"no": "③", "title": "外部注入来源", "style": "inject", "lines": lines})
    # 4 sensitive read: SECRET content flowing into the focused call
    secret_contents = [nodes[s] for s in into(focus_call.id, "FLOWS_INTO")]
    for secret in secret_contents:
        reader = nodes[into(secret.id, "RETURNS")[0]]
        decision = nodes[reader.attrs["decision_node"]]
        resource = reader.attrs["params"].get("resource", secret.attrs["source_id"])
        resource_label = "~/" + resource.split("/home/", 1)[1] if "/home/" in resource else resource
        steps.append(
            {
                "no": "④",
                "title": "读取私钥（敏感数据）",
                "style": "sensitive",
                "lines": [
                    f"{reader.attrs['mcp_server']} MCP · {reader.attrs['tool'].split('.', 1)[-1]}",
                    f"目标：{resource_label}",
                    f"决策：{'放行' if decision.attrs['decision'] == 'ALLOW' else decision.attrs['decision']}"
                    f"（在授权范围内）",
                    f"结果标记：{secret.attrs['confidentiality']}（敏感数据）",
                ],
            }
        )
        break
    # 5 egress attempt (focus)
    url = focus_call.attrs["params"].get("url", "")
    host = _host(url) if url else ", ".join(out(focus.id, "PREVENTED_EFFECT")) or "?"
    why = []
    if secret_contents:
        why.append("请求参数含私钥数据（来自步骤④）")
    alignment = focus.attrs.get("alignment") or {}
    if focus.attrs["reason"] == "RESOURCE_OUT_OF_SCOPE":
        scopes = next(
            (
                f["summary"]
                for f in alignment.get("facts", [])
                if f["field"] == "grant.resource_scopes"
            ),
            "",
        )
        allowed = [_host(s) for s in scopes.split(", ") if s.startswith("http")]
        why.append(
            f"目标域名 {host} 不在白名单" + (f"（仅允许 {'、'.join(allowed)}）" if allowed else "")
        )
    else:
        why.append(ZH_BLOCK_REASON.get(focus.attrs["reason"], focus.attrs["reason"]))
    risk = focus.attrs["provenance_risk"]["level"]
    steps.append(
        {
            "no": "⑤",
            "title": "外发请求 → 阻断",
            "style": "block",
            "lines": [
                f"{focus_call.attrs['tool']} → {host}",
                f"决策：阻断（{ZH_BLOCK_REASON.get(focus.attrs['reason'], focus.attrs['reason'])}）"
                f"  风险：{risk}",
                *("原因：" + w if i == 0 else "　　　" + w for i, w in enumerate(why)),
            ],
        }
    )
    # side: later blocked retries by the same agent with the same tool
    retries = []
    for node in sorted(nodes.values(), key=lambda n: n.seq):
        if (
            node.type == "tool_call"
            and node.seq > focus_call.seq
            and node.attrs["agent"] == focus_call.attrs["agent"]
            and node.attrs["tool"] == focus_call.attrs["tool"]
        ):
            decision = nodes.get(node.attrs.get("decision_node", ""))
            if decision is not None and decision.attrs["decision"] == "BLOCK":
                retry_host = _host(node.attrs["params"].get("url", ""))
                retries.append(
                    {
                        "title": "第二次尝试：换合法域名重试",
                        "style": "block",
                        "lines": [
                            f"{node.attrs['tool']} → {retry_host}",
                            f"决策：阻断（{ZH_BLOCK_REASON.get(decision.attrs['reason'], decision.attrs['reason'])}）",
                            "私钥数据不允许外传，换域名也无效",
                        ],
                    }
                )
    # result
    routed = [
        e
        for e in graph.edges
        if e.type == "ROUTED_TO"
        and nodes[e.src].attrs["tool"] == focus_call.attrs["tool"]
        and nodes[e.src].attrs["agent"] == focus_call.attrs["agent"]
    ]
    server = focus_call.attrs["mcp_server"]
    reached = any(e.attrs.get("executed") for e in routed)
    result = {
        "title": "影响结果",
        "style": "result" if not reached else "block",
        "lines": [
            f"外发{'已到达' if reached else '未到达'} {server} MCP",
            f"{len(routed)} 次外发尝试，{sum(bool(e.attrs.get('executed')) for e in routed)} 次被执行",
        ],
    }
    return {"steps": steps, "retries": retries, "result": result}


def _zh_label_html(item: dict, header: str) -> str:
    fill, stroke, color = ZH_STYLES[item["style"]]
    rows = [
        f'<TR><TD ALIGN="LEFT"><B><FONT POINT-SIZE="22">{html.escape(header)}</FONT></B></TD></TR>'
    ]
    for line in item["lines"]:
        rows.append(
            f'<TR><TD ALIGN="LEFT"><FONT POINT-SIZE="16">{html.escape(line)}</FONT></TD></TR>'
        )
    return (
        '<<TABLE BORDER="0" CELLBORDER="0" CELLSPACING="2" CELLPADDING="2">'
        + "".join(rows)
        + "</TABLE>>"
    )


def to_simple_dot_zh(graph: ProvenanceGraph) -> str:
    data = simple_attack_path_zh(graph)
    out = [
        "digraph attack_path_zh {",
        f'  graph [rankdir=TB, nodesep=0.8, ranksep=0.55, fontname="{ZH_FONT}", fontsize=26,'
        ' labelloc=t, label="攻击路径（简化版）：间接注入 → 委派 → 读私钥 → 外发被阻断",'
        ' pad=0.4, bgcolor="white"];',
        f'  node [shape=box, style="rounded,filled", fontname="{ZH_FONT}", margin="0.3,0.18",'
        " penwidth=2.5];",
        f'  edge [fontname="{ZH_FONT}", fontsize=15, penwidth=2.2, color="#64748b",'
        " arrowsize=1.2];",
    ]
    ids = []
    for index, step in enumerate(data["steps"]):
        fill, stroke, color = ZH_STYLES[step["style"]]
        node_id = f"s{index}"
        ids.append(node_id)
        out.append(
            f"  {node_id} [label={_zh_label_html(step, step['no'] + ' ' + step['title'])},"
            f' fillcolor="{fill}", color="{stroke}", fontcolor="{color}"];'
        )
    result = data["result"]
    fill, stroke, color = ZH_STYLES[result["style"]]
    out.append(
        f'  result [label={_zh_label_html(result, result["title"])}, fillcolor="{fill}",'
        f' color="{stroke}", fontcolor="{color}"];'
    )
    for a, b in zip(ids, ids[1:]):
        out.append(f"  {a} -> {b} [weight=10];")
    out.append(f"  {ids[-1]} -> result [weight=10];")
    for index, retry in enumerate(data["retries"][:1]):
        fill, stroke, color = ZH_STYLES[retry["style"]]
        out.append(
            f"  r{index} [label={_zh_label_html(retry, retry['title'])},"
            f' fillcolor="{fill}", color="{stroke}", fontcolor="{color}", style="rounded,filled,dashed"];'
        )
        out.append(f"  {{ rank=same; {ids[-1]}; r{index}; }}")
        out.append(
            f'  {ids[-1]} -> r{index} [style=dashed, label="  被拒后重试  ",'
            ' color="#7f1d1d", fontcolor="#7f1d1d", constraint=false];'
        )
    out.append("}")
    return "\n".join(out) + "\n"


def to_simple_mermaid_zh(graph: ProvenanceGraph) -> str:
    data = simple_attack_path_zh(graph)
    lines = ["flowchart TB"]
    ids = []
    for index, step in enumerate(data["steps"]):
        label = "<br/>".join(_mm_text(x) for x in [f"{step['no']} {step['title']}", *step["lines"]])
        lines.append(f'    s{index}["{label}"]')
        ids.append((f"s{index}", step["style"]))
    result = data["result"]
    label = "<br/>".join(_mm_text(x) for x in [result["title"], *result["lines"]])
    lines.append(f'    result["{label}"]')
    chain = [i for i, _ in ids] + ["result"]
    lines.append("    " + " --> ".join(chain))
    for index, retry in enumerate(data["retries"][:1]):
        label = "<br/>".join(_mm_text(x) for x in [retry["title"], *retry["lines"]])
        lines.append(f'    r{index}["{label}"]')
        lines.append(f"    {ids[-1][0]} -.->|被拒后重试| r{index}")
        ids.append((f"r{index}", retry["style"]))
    for style, (fill, stroke, color) in ZH_STYLES.items():
        lines.append(
            f"    classDef {style} fill:{fill},stroke:{stroke},color:{color},stroke-width:2px"
        )
    for node_id, style in [*ids, ("result", result["style"])]:
        lines.append(f"    class {node_id} {style}")
    return "\n".join(lines) + "\n"


def export_simple_attack_path_zh(graph: ProvenanceGraph, out_dir: Path) -> list[Path]:
    """Write attack_path_simple_zh.{dot,mmd,svg,png}; svg/png only when Graphviz exists."""
    out_dir.mkdir(parents=True, exist_ok=True)
    dot = to_simple_dot_zh(graph)
    files: dict[str, str | bytes] = {
        "attack_path_simple_zh.dot": dot,
        "attack_path_simple_zh.mmd": to_simple_mermaid_zh(graph),
    }
    svg = render_dot(dot, "svg")
    if svg is not None:
        files["attack_path_simple_zh.svg"] = svg
        png = render_dot(
            dot.replace(
                "digraph attack_path_zh {", "digraph attack_path_zh {\n  graph [dpi=144];", 1
            ),
            "png",
        )
        if png is not None:
            files["attack_path_simple_zh.png"] = png
    written = []
    for name, data in files.items():
        path = out_dir / name
        if isinstance(data, bytes):
            path.write_bytes(data)
        else:
            path.write_text(data, "utf-8")
        written.append(path)
    return written
