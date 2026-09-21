#!/usr/bin/env python3
"""Ownership-plan primitives for the shared installer.

Read-only planner: given a source (a whole tree or a single file), a
destination, and the destination root's provenance ledger, classify
every candidate destination BEFORE anything is written:

  create     destination absent
  update     destination differs, ledger proves a prior deploy
  unchanged  destination identical, ledger proves a prior deploy
  delete     destination no longer shipped, ledger proves a prior deploy
  refuse     destination present without ledger proof

Ownership is the .spec-dev-kit-deployed discipline sync.sh already
applies, made mechanical: a destination is owned only when its relative
path AND its current sha256 match one `<sha256> <path>` ledger line.
Content equality is not ownership — an identical but unledgered
destination is refused, never silently adopted.

The module never writes; preflight and dry-run reporting consume the
same plan. Exit status: 0 no refusal, 1 the plan contains refusals,
2 usage or validation error (stderr).

    tools/ownership.py plan-tree --src skills/<name> --dest <root>/<name>
    tools/ownership.py plan-file --src <file> --dest <file> [--name KEY]
"""
import argparse
import hashlib
import os
import sys
from collections import namedtuple
from pathlib import Path

LEDGER_NAME = ".spec-dev-kit-deployed"

CREATE = "create"
UPDATE = "update"
UNCHANGED = "unchanged"
DELETE = "delete"
REFUSE = "refuse"

# kind is one of the five decisions above; name is the ledger key (the
# destination's relative path for trees, the root's own key for single
# files); src_sha/dest_sha are None when the source/destination is
# absent, so refuse reasons stay derivable from the tuple alone.
Decision = namedtuple("Decision", "kind name src_sha dest_sha")

_HEX = set("0123456789abcdef")


def sha256_file(path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_ledger(path) -> dict:
    """name -> sha256 of what a prior deploy left at that name; {} when
    no ledger exists. Malformed or duplicated lines raise ValueError:
    the ledger is the ownership authority, so a corrupt one must fail
    the plan instead of silently mis-classifying it."""
    path = Path(path)
    if not path.exists():
        return {}
    entries = {}
    for lineno, line in enumerate(path.read_text().splitlines(), 1):
        if not line.strip():
            continue
        sha, sep, name = line.partition(" ")
        if (not sep or not name or len(sha) != 64
                or any(c not in _HEX for c in sha)):
            raise ValueError(f"{path}:{lineno}: malformed ledger line {line!r}")
        if name in entries:
            raise ValueError(f"{path}:{lineno}: duplicate ledger entry {name!r}")
        entries[name] = sha
    return entries


def classify(name, src_sha, dest_sha, ledger):
    """One destination's Decision from its ledger key, its source sha
    (None when unshipped), its current sha (None when absent), and the
    root's ledger mapping."""
    if dest_sha is None:
        return Decision(CREATE, name, src_sha, None)
    owned = ledger.get(name) == dest_sha
    if src_sha is None:
        return Decision(DELETE if owned else REFUSE, name, None, dest_sha)
    if src_sha == dest_sha:
        return Decision(UNCHANGED if owned else REFUSE, name, src_sha, dest_sha)
    return Decision(UPDATE if owned else REFUSE, name, src_sha, dest_sha)


def inventory(root):
    """Sorted relative paths of the regular files under root — the same
    population sync.sh's find predicates see: .DS_Store, __pycache__/,
    and ledger files are invisible; symlinks are skipped, not followed.
    A missing root yields [] (fresh destination)."""
    root = Path(root)
    found = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(
            d for d in dirnames
            if d != "__pycache__" and not (Path(dirpath) / d).is_symlink())
        for f in sorted(filenames):
            if f == ".DS_Store" or f.startswith(LEDGER_NAME):
                continue
            p = Path(dirpath) / f
            if p.is_symlink() or not p.is_file():
                continue
            found.append(p.relative_to(root).as_posix())
    return sorted(found)


def _dest_sha(dest: Path):
    """sha of a destination occupant, or (True, None) when the path is
    occupied by something a deploy must not touch (symlink, directory,
    any non-regular file)."""
    if os.path.lexists(dest) and (dest.is_symlink() or not dest.is_file()):
        return True, None
    if dest.is_file():
        return False, sha256_file(dest)
    return False, None


def plan_tree(src_dir, dest_dir, ledger_file=None):
    """Decisions for every name in the union of the source and
    destination inventories; the ledger defaults to dest_dir/LEDGER_NAME.
    Raises ValueError for a missing source or corrupt ledger."""
    src_dir, dest_dir = Path(src_dir), Path(dest_dir)
    if not src_dir.is_dir():
        raise ValueError(f"{src_dir}: source tree missing")
    ledger = read_ledger(ledger_file or dest_dir / LEDGER_NAME)
    src_names = set(inventory(src_dir))
    decisions = []
    for name in sorted(src_names | set(inventory(dest_dir))):
        dest = dest_dir / name
        src_sha = sha256_file(src_dir / name) if name in src_names else None
        blocked, dest_sha = _dest_sha(dest)
        if blocked:
            decisions.append(Decision(REFUSE, name, src_sha, None))
        else:
            decisions.append(classify(name, src_sha, dest_sha, ledger))
    return decisions


def plan_file(src_file, dest_file, name=None, ledger_file=None):
    """One Decision for a file-to-file destination. name is the ledger
    key and defaults to the destination filename — command roots key on
    the extension-less base, so pass it there. The ledger defaults to
    the destination's parent/LEDGER_NAME."""
    src_file, dest_file = Path(src_file), Path(dest_file)
    if not src_file.is_file():
        raise ValueError(f"{src_file}: source file missing")
    ledger = read_ledger(ledger_file or dest_file.parent / LEDGER_NAME)
    blocked, dest_sha = _dest_sha(dest_file)
    if blocked:
        return Decision(REFUSE, name or dest_file.name, sha256_file(src_file), None)
    return classify(name or dest_file.name, sha256_file(src_file), dest_sha, ledger)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        prog="ownership.py",
        description="Plan destination ownership before any write (read-only).")
    sub = ap.add_subparsers(dest="cmd", required=True)

    tree = sub.add_parser("plan-tree", help="plan a source tree into a destination dir")
    tree.add_argument("--src", required=True, metavar="DIR")
    tree.add_argument("--dest", required=True, metavar="DIR")
    tree.add_argument("--ledger", metavar="FILE",
                      help="defaults to <dest>/" + LEDGER_NAME)

    one = sub.add_parser("plan-file", help="plan one source file into a destination file")
    one.add_argument("--src", required=True, metavar="FILE")
    one.add_argument("--dest", required=True, metavar="FILE")
    one.add_argument("--name", metavar="KEY",
                     help="ledger key; defaults to the destination filename")
    one.add_argument("--ledger", metavar="FILE",
                     help="defaults to the destination's parent/" + LEDGER_NAME)

    args = ap.parse_args(argv)
    try:
        if args.cmd == "plan-tree":
            decisions = plan_tree(args.src, args.dest, args.ledger)
        else:
            decisions = [plan_file(args.src, args.dest, args.name, args.ledger)]
    except (ValueError, OSError) as e:
        print(f"ERROR {e}", file=sys.stderr)
        return 2
    for d in decisions:
        print(f"{d.kind} {d.name}")
    return 1 if any(d.kind == REFUSE for d in decisions) else 0


if __name__ == "__main__":
    sys.exit(main())
