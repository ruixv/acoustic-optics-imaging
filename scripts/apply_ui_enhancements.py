#!/usr/bin/env python3
"""Re-apply progressive UI assets after scripts/build_site.py rewrites HTML."""
from __future__ import annotations
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def once(text: str, old: str, new: str) -> str:
    return text if new in text else text.replace(old, new, 1)


def patch_index() -> None:
    path = ROOT / "index.html"
    text = path.read_text(encoding="utf-8")
    text = once(
        text,
        '<link rel="stylesheet" href="style.css">',
        '<link rel="stylesheet" href="style.css"><link rel="stylesheet" href="enhancements.css"><link rel="stylesheet" href="author_graph_interactions.css">',
    )
    text = once(
        text,
        '<script src="script.js" defer></script></body>',
        '<script src="script.js" defer></script><script src="enhancements.js" defer></script><script src="author_graph_interactions.js" defer></script><script src="graph_label_cleanup.js" defer></script></body>',
    )
    path.write_text(text, encoding="utf-8")


def patch_paper() -> None:
    path = ROOT / "paper.html"
    text = path.read_text(encoding="utf-8")
    text = once(
        text,
        "<link rel='stylesheet' href='style.css'>",
        "<link rel='stylesheet' href='style.css'><link rel='stylesheet' href='author_graph_interactions.css'>",
    )
    text = once(
        text,
        "<script src='script.js' defer></script></body>",
        "<script src='script.js' defer></script><script src='author_graph_interactions.js' defer></script><script src='graph_label_cleanup.js' defer></script></body>",
    )
    path.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    patch_index()
    patch_paper()
    print("Applied progressive UI enhancements to index.html and paper.html")
