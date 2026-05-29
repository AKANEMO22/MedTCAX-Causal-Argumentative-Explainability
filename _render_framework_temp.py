from __future__ import annotations

import math
import re
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import networkx as nx
import pydot


ROOT = Path(__file__).resolve().parent
OUTPUT_DIR = ROOT / "causal_argumentation-main" / "outputs_heart_disease" / "fci_experiment"


DOT_FILES = [
    "discovery_fci_dropfirst_weighted",
    "discovery_fci_droplast_weighted",
    "merged_groups_fci_weighted",
    "final_unified_fci_weighted",
]


DOT_TITLES = {
    "discovery_fci_dropfirst_weighted": "Discovery FCI Drop-First Weighted",
    "discovery_fci_droplast_weighted": "Discovery FCI Drop-Last Weighted",
    "merged_groups_fci_weighted": "Merged Groups FCI Weighted",
    "final_unified_fci_weighted": "Final Unified FCI Weighted",
}

FRAMEWORK_FILES = [
    "framework.apx",
    "framework.tgf",
]


def _normalize_graph(graph: pydot.Dot, title: str | None = None) -> pydot.Dot:
    graph.set_rankdir("LR")
    graph.set_splines("spline")
    graph.set_overlap("false")
    graph.set_pad("0.35")
    graph.set_nodesep("0.35")
    graph.set_ranksep("0.75")
    graph.set_bgcolor("white")
    graph.set_fontname("Helvetica")
    graph.set_dpi("220")
    if title:
        graph.set_label(title)
        graph.set_labelloc("t")
        graph.set_labeljust("c")
        graph.set_fontsize("22")

    for node in graph.get_nodes():
        node.set_fontname("Helvetica")
        node.set_fontsize("12")
        if not node.get_shape():
            node.set_shape("ellipse")
        if not node.get_style():
            node.set_style("filled")
        if not node.get_fillcolor():
            node.set_fillcolor("#f4f8ff")
        if not node.get_color():
            node.set_color("#8aa0c4")
        if not node.get_margin():
            node.set_margin("0.08,0.05")

    for edge in graph.get_edges():
        edge.set_arrowsize(edge.get_arrowsize() or "0.8")
        edge.set_fontname("Helvetica")
        edge.set_fontsize(edge.get_fontsize() or "11")

    return graph


def _label_weight(edge: pydot.Edge) -> float | None:
    label = edge.get_label()
    if not label:
        return None
    match = re.search(r"[-+]?[0-9]*\.?[0-9]+", str(label))
    if not match:
        return None
    try:
        return float(match.group(0))
    except ValueError:
        return None


def _set_edge_style(edge: pydot.Edge, weight: float | None) -> None:
    if weight is None:
        edge.set_style(edge.get_style() or "solid")
        return

    edge.set_color("#2e7d32" if weight >= 0 else "#c62828")
    edge.set_penwidth(str(1.0 + 4.0 * min(abs(weight), 1.0)))
    if abs(weight) < 0.10:
        edge.set_style("dashed")


def _parse_root(name: str) -> str:
    if "[" in name and name.endswith(")"):
        return name.split("[", 1)[0]
    if "_" in name:
        return name.rsplit("_", 1)[0]
    return name


def _parse_apx(path: Path) -> nx.DiGraph:
    graph = nx.DiGraph()
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("arg(") and line.endswith(")."):
            name = line[4:-2]
            graph.add_node(name)
        elif line.startswith("att(") and line.endswith(")."):
            payload = line[4:-2]
            if "," not in payload:
                continue
            src, tgt = payload.split(",", 1)
            graph.add_edge(src, tgt, weight=1.0)
    return graph


def _parse_tgf(path: Path) -> nx.DiGraph:
    graph = nx.DiGraph()
    before_edges = True
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line == "#":
            before_edges = False
            continue
        if before_edges:
            graph.add_node(line)
        else:
            parts = line.split()
            if len(parts) >= 2:
                graph.add_edge(parts[0], parts[1], weight=1.0)
    return graph


def _dot_to_nx(source_path: Path) -> nx.DiGraph:
    graphs = pydot.graph_from_dot_file(str(source_path))
    if not graphs:
        raise RuntimeError(f"Unable to parse DOT file: {source_path}")

    dot_graph = graphs[0]
    graph = nx.DiGraph()

    for node in dot_graph.get_nodes():
        name = node.get_name().strip('"')
        if name in {"node", "graph", "edge", "\n"}:
            continue
        graph.add_node(name)

    for edge in dot_graph.get_edges():
        src = edge.get_source().strip('"')
        tgt = edge.get_destination().strip('"')
        if not src or not tgt:
            continue
        graph.add_edge(
            src,
            tgt,
            weight=_label_weight(edge) or 1.0,
            label=str(edge.get_label() or "").strip('"'),
        )

    return graph


def _render_graphviz_dot(source_path: Path, output_path: Path, title: str | None = None) -> None:
    graph = _dot_to_nx(source_path)
    node_count = graph.number_of_nodes()

    fig_width = max(16, min(28, 10 + node_count * 0.32))
    fig_height = max(12, min(22, 8 + node_count * 0.26))

    plt.figure(figsize=(fig_width, fig_height), facecolor="white")
    pos = nx.spring_layout(graph, seed=42, k=1.5, iterations=140)

    nx.draw_networkx_edges(
        graph,
        pos,
        edge_color=["#2e7d32" if data.get("weight", 1.0) >= 0 else "#c62828" for _, _, data in graph.edges(data=True)],
        width=[1.0 + 3.5 * min(abs(float(data.get("weight", 1.0))), 1.0) for _, _, data in graph.edges(data=True)],
        alpha=0.58,
        arrowsize=16,
        arrowstyle="->",
        connectionstyle="arc3,rad=0.04",
    )

    labels = {node: node for node in graph.nodes}
    label_font_size = 8 if node_count > 18 else 9
    for node, (x, y) in pos.items():
        plt.text(
            x,
            y,
            labels[node],
            fontsize=label_font_size,
            fontweight="bold",
            ha="center",
            va="center",
            bbox=dict(
                boxstyle="round,pad=0.28",
                facecolor="#f4f8ff",
                edgecolor="#8aa0c4",
                linewidth=1.1,
                alpha=0.96,
            ),
        )

    for src, tgt, data in graph.edges(data=True):
        weight = float(data.get("weight", 1.0))
        if abs(weight) < 0.25:
            continue
        mid_x = (pos[src][0] + pos[tgt][0]) / 2
        mid_y = (pos[src][1] + pos[tgt][1]) / 2
        plt.text(
            mid_x,
            mid_y,
            f"{weight:+.2f}",
            fontsize=8,
            color="#8b0000" if weight >= 0 else "#b71c1c",
            ha="center",
            va="center",
            bbox=dict(boxstyle="round,pad=0.22", facecolor="white", edgecolor="#444444", alpha=0.92),
        )

    plt.title(title or source_path.stem, fontsize=18, fontweight="bold", pad=18)
    plt.axis("off")
    plt.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=220, bbox_inches="tight")
    plt.close()
    print(f"Saved: {output_path}")


def _draw_argumentation_graph(graph: nx.DiGraph, output_path: Path, title: str) -> None:
    if graph.number_of_nodes() == 0:
        raise RuntimeError("Graph is empty; nothing to render.")

    node_count = graph.number_of_nodes()
    fig_width = max(14, min(22, 8 + node_count * 0.28))
    fig_height = max(10, min(18, 6 + node_count * 0.22))

    plt.figure(figsize=(fig_width, fig_height), facecolor="white")
    pos = nx.spring_layout(graph, seed=42, k=1.6, iterations=120)

    roots = {_parse_root(node) for node in graph.nodes}
    labels = {node: node for node in graph.nodes}

    nx.draw_networkx_nodes(
        graph,
        pos,
        node_color="#ef8d8d",
        node_size=max(1800, 3600 - node_count * 18),
        alpha=0.90,
        linewidths=1.2,
        edgecolors="#d66b6b",
    )
    nx.draw_networkx_labels(graph, pos, labels=labels, font_size=12, font_weight="bold")

    for src, tgt, data in graph.edges(data=True):
        weight = float(data.get("weight", 1.0))
        same_root = _parse_root(src) == _parse_root(tgt)
        if same_root:
            edge_color = "#9e9e9e"
            alpha = 0.28
        else:
            edge_color = "#ff1f1f"
            alpha = 0.58

        nx.draw_networkx_edges(
            graph,
            pos,
            edgelist=[(src, tgt)],
            edge_color=edge_color,
            width=1.0 + 3.5 * abs(weight),
            alpha=alpha,
            arrowsize=16,
            arrowstyle="->",
            connectionstyle="arc3,rad=0.05",
        )

        if not same_root and abs(weight) >= 0.20:
            mid_x = (pos[src][0] + pos[tgt][0]) / 2
            mid_y = (pos[src][1] + pos[tgt][1]) / 2
            offset = 0.02 if (src, tgt) in graph.edges else 0.0
            plt.text(
                mid_x,
                mid_y + offset,
                f"{weight:.2f}",
                fontsize=10,
                color="#8b0000",
                ha="center",
                va="center",
                bbox=dict(boxstyle="round,pad=0.25", facecolor="white", edgecolor="#444444", alpha=0.92),
            )

    plt.title(title, fontsize=18, fontweight="bold", pad=18)
    plt.axis("off")
    plt.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=220, bbox_inches="tight")
    plt.close()
    print(f"Saved: {output_path}")


def main() -> None:
    if not OUTPUT_DIR.exists():
        raise SystemExit(f"Output directory not found: {OUTPUT_DIR}")

    for stem in DOT_FILES:
        source = OUTPUT_DIR / f"{stem}.dot"
        if not source.exists():
            print(f"Skipping missing DOT file: {source}")
            continue
        pretty_name = DOT_TITLES.get(stem, stem.replace("_", " ").title())
        _render_graphviz_dot(source, OUTPUT_DIR / f"{stem}.png", title=pretty_name)

    for name in FRAMEWORK_FILES:
        source = OUTPUT_DIR / name
        if not source.exists():
            print(f"Skipping missing framework file: {source}")
            continue

        if source.suffix == ".apx":
            graph = _parse_apx(source)
            _draw_argumentation_graph(
                graph,
                OUTPUT_DIR / "framework_apx.png",
                title="Classical AF (Unified encoded graph) — Semi-stable",
            )
            _draw_argumentation_graph(
                graph,
                OUTPUT_DIR / "framework.png",
                title="Classical AF (Unified encoded graph) — Semi-stable",
            )
        else:
            graph = _parse_tgf(source)
            _draw_argumentation_graph(
                graph,
                OUTPUT_DIR / "framework_tgf.png",
                title="Classical AF (Unified encoded graph) — Semi-stable",
            )


if __name__ == "__main__":
    main()