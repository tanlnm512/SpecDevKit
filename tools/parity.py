#!/usr/bin/env python3
"""Shared-core parity — one master, committed replica views.

The parity closure lives ONCE in the master directory
skills/spec-shape/scripts/ and is enumerated by import scan, never a
hand list: the seeds are graph.py, check.py, contract.py,
specstate.py, telemetry.py and freeze.py, and any local sibling
module those files import — transitively, to fixpoint — joins the
closure mechanically (D-004, specs/spec-to-prod-split/tech-spec.md).

This tool replicates the closure into the scripts/ of every other
skill that ships graph.py (discovery keyed on graph.py alone, so a
check.py-only skill stays out) as byte-identical committed views.
Replicas are regenerate-only: never edit one — edit the master,
rerun this tool, rerun drift-check. It never creates a SKILL.md.

--check verifies every replica closure file is byte-identical to the
master's, naming the skill and file on any drift or missing file.

Exit: 0 parity holds · 1 drift · 2 usage or master error.
"""
from __future__ import annotations

import argparse
import ast
import shutil
import sys
from pathlib import Path

PKG_ROOT = Path(__file__).resolve().parent.parent
MASTER = PKG_ROOT / "skills" / "spec-shape" / "scripts"
SEEDS = ("graph.py", "check.py", "contract.py", "specstate.py",
         "telemetry.py", "freeze.py")


def sibling_imports(tree: ast.AST) -> set[str]:
    """Module roots an AST imports absolutely, plus relative-import
    names (level >= 1) — candidates for sibling-module membership."""
    roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                roots.add(node.module.split(".")[0])
            if node.level:
                roots.update(alias.name.split(".")[0] for alias in node.names)
    return roots


def closure() -> list[str]:
    """The parity closure: seeds plus every sibling .py they import,
    transitively, to fixpoint."""
    names = set(SEEDS)
    pending = list(SEEDS)
    while pending:
        path = MASTER / pending.pop()
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for root in sibling_imports(tree):
            candidate = f"{root}.py"
            if candidate not in names and (MASTER / candidate).is_file():
                names.add(candidate)
                pending.append(candidate)
    return sorted(names)


def replica_scripts_dirs() -> list[Path]:
    """scripts/ of every graph.py-shipping skill except the master."""
    return sorted(
        graph.parent for graph in (PKG_ROOT / "skills").glob("*/scripts/graph.py")
        if graph.parent != MASTER)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="parity.py",
        description="Replicate the shared-core closure from "
                    "skills/spec-shape/scripts/ into every other "
                    "graph.py-shipping skill's scripts/, or --check the "
                    "replicas against the master.")
    p.add_argument("--check", action="store_true",
                   help="verify every replica closure file is "
                        "byte-identical to the master's; exit 1 on drift")
    args = p.parse_args(argv)

    missing = [name for name in SEEDS if not (MASTER / name).is_file()]
    if not MASTER.is_dir() or missing:
        print(f"error: master {MASTER.relative_to(PKG_ROOT)} is missing "
              f"its closure: {', '.join(missing) or 'directory absent'}",
              file=sys.stderr)
        return 2

    files = closure()
    targets = replica_scripts_dirs()
    if args.check:
        rc = 0
        for name in files:
            master_bytes = (MASTER / name).read_bytes()
            for scripts_dir in targets:
                replica = scripts_dir / name
                skill = scripts_dir.parent.name
                rel = replica.relative_to(PKG_ROOT)
                if not replica.is_file():
                    print(f"DRIFT {rel} — missing from skill {skill} "
                          f"(master ships it); rerun tools/parity.py")
                    rc = 1
                elif replica.read_bytes() != master_bytes:
                    print(f"DRIFT {rel} — differs from master "
                          f"skills/spec-shape/scripts/{name}; rerun "
                          "tools/parity.py")
                    rc = 1
        if not rc:
            print(f"parity: OK — {len(files)} closure files x "
                  f"{len(targets)} replica skills byte-identical to "
                  f"{MASTER.relative_to(PKG_ROOT)}")
        return rc

    for scripts_dir in targets:
        scripts_dir.mkdir(parents=True, exist_ok=True)
        for name in files:
            replica = scripts_dir / name
            shutil.copyfile(MASTER / name, replica)
            print(f"wrote {replica.relative_to(PKG_ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
