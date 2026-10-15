#!/usr/bin/env python3
"""Collect the git facts a changelog needs for a commit range.

Usage:
    collect.py <from> [<to>] [--exclusive]

<from> is INCLUSIVE by default ("ตั้งแต่ commit X" includes X); pass
--exclusive to start after it. <to> defaults to HEAD.

Prints Markdown: commits (with PR numbers), modules touched per commit,
version bumps, new modules (auto_install + depends), changed-but-unbumped
modules, added migrations and added ADR/docs files.
"""

import ast
import re
import subprocess
import sys


def git(*args):
    return subprocess.run(
        ["git", *args], capture_output=True, text=True, check=True
    ).stdout


def manifest_at(ref, module):
    try:
        src = git("show", f"{ref}:{module}/__manifest__.py")
    except subprocess.CalledProcessError:
        return None
    try:
        return ast.literal_eval(src.strip())
    except (ValueError, SyntaxError):
        return {}


def modules_in(paths):
    return sorted({p.split("/", 1)[0] for p in paths if "/" in p})


def main(argv):
    args = [a for a in argv if not a.startswith("--")]
    if not args:
        sys.exit(__doc__)
    start, end = args[0], (args[1] if len(args) > 1 else "HEAD")
    base = start if "--exclusive" in argv else f"{start}^"
    rng = f"{base}..{end}"

    print(f"# Range `{rng}`\n")

    print("## Commits (oldest first)\n")
    log = git("log", "--reverse", "--format=%h%x09%ad%x09%s", "--date=short", rng)
    for line in log.splitlines():
        sha, date, subject = line.split("\t", 2)
        files = git("show", "--name-only", "--format=", sha).split()
        pr = re.search(r"\(#(\d+)\)\s*$", subject)
        print(f"- `{sha}` {date} {subject}")
        print(f"  - PR: {'#' + pr.group(1) if pr else '-'}")
        print(f"  - modules: {', '.join(modules_in(files)) or '-'}")
    print()

    changed = git("diff", "--name-only", rng).split()
    touched = [m for m in modules_in(changed) if not m.startswith(".")]

    bumps, new, unbumped = [], [], []
    for mod in touched:
        after = manifest_at(end, mod)
        if after is None:
            continue  # not a module (docs/, setup/, removed module…)
        before = manifest_at(base, mod)
        if before is None:
            new.append((mod, after))
        elif before.get("version") != after.get("version"):
            bumps.append((mod, before.get("version"), after.get("version")))
        else:
            unbumped.append(mod)

    print("## Version bumps\n")
    for mod, old, new_v in bumps:
        print(f"- `{mod}` {old} → {new_v}")
    print("- (none)\n" if not bumps else "")

    print("## New modules (need `-i`; `-u` never installs a new module)\n")
    for mod, man in new:
        print(
            f"- `{mod}` {man.get('version')} auto_install="
            f"{man.get('auto_install', False)} depends={man.get('depends', [])}"
        )
    print("- (none)\n" if not new else "")

    print("## Changed without a version bump\n")
    for mod in unbumped:
        files = [f for f in changed if f.startswith(mod + "/")]
        kinds = sorted({f.rsplit(".", 1)[-1] for f in files if "." in f})
        print(f"- `{mod}` ({', '.join(kinds)})")
    print("- (none)\n" if not unbumped else "")

    added = git("diff", "--name-only", "--diff-filter=A", rng).split()
    print("## Added migrations\n")
    migs = [f for f in added if "/migrations/" in f]
    print("\n".join(f"- `{f}`" for f in migs) or "- (none)")
    print("\n## Added ADR / docs\n")
    docs = [
        f for f in added if "/adr/" in f or f.endswith(("CONTEXT.md", "README.rst"))
    ]
    print("\n".join(f"- `{f}`" for f in docs) or "- (none)")


if __name__ == "__main__":
    main(sys.argv[1:])
