"""Regression test for the Phase 0 inward dependency boundary."""

import ast
from pathlib import Path

from nfl_fantasy_assistant.domain import DraftId


def test_domain_imports_without_outer_adapters() -> None:
    assert DraftId("draft-1").value == "draft-1"

    domain_root = Path(__file__).parents[1] / "src" / "nfl_fantasy_assistant" / "domain"
    prohibited_roots = {"fastapi", "sqlite3", "polars", "nflreadpy"}
    for source_path in domain_root.glob("*.py"):
        tree = ast.parse(source_path.read_text(encoding="utf-8"))
        imports = [
            alias.name.split(".", maxsplit=1)[0]
            for node in ast.walk(tree)
            if isinstance(node, (ast.Import, ast.ImportFrom))
            for alias in node.names
        ]
        assert prohibited_roots.isdisjoint(imports), source_path
