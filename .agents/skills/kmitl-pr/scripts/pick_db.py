#!/usr/bin/env python3
"""Rank sandbox source databases newest first, by the date in their name.

Reads `odoo_sandbox.sh dbs` output (`name|size` per line) on stdin and prints
one `date  name` line per candidate, newest first. Names without a date
(e.g. `devel`) come last. Skipped: postgres, template*, cache-*, sbx_*.

Date formats recognised in a name (first match wins):
  YYYYMMDD[HHMM]   ok_uat-20260930, pre-production-202610150941
  YYYY-MM-DD       uat-2026-09-30
  DD-MM-YYYY       uat-30-09-2026
  DD-MM-YY         uat-30-09-26
Separators may be "-", "_" or ".".

Usage:  odoo_sandbox.sh dbs | pick_db.py
"""
import re
import sys
from datetime import datetime

SKIP = re.compile(r"^(postgres|template\d*|cache-.*|sbx_.*)$")
SEP = r"[-_.]"
PATTERNS = [
    (re.compile(r"(?<!\d)(20\d{2})(\d{2})(\d{2})(?:\d{4})?(?!\d)"), "ymd"),
    (re.compile(rf"(?<!\d)(20\d{{2}}){SEP}(\d{{1,2}}){SEP}(\d{{1,2}})(?!\d)"), "ymd"),
    (re.compile(rf"(?<!\d)(\d{{1,2}}){SEP}(\d{{1,2}}){SEP}(20\d{{2}})(?!\d)"), "dmy"),
    (re.compile(rf"(?<!\d)(\d{{1,2}}){SEP}(\d{{1,2}}){SEP}(\d{{2}})(?!\d)"), "dmy2"),
]
# Same date: richer workflow data first.
KIND_ORDER = ("ok_uat", "uat", "pre-production", "pre_production")


def parse_date(name):
    for rx, order in PATTERNS:
        for m in rx.finditer(name):
            a, b, c = (int(x) for x in m.groups())
            y, mth, d = {
                "ymd": (a, b, c),
                "dmy": (c, b, a),
                "dmy2": (2000 + c, b, a),
            }[order]
            try:
                return datetime(y, mth, d)
            except ValueError:
                continue
    return None


def kind_rank(name):
    for i, k in enumerate(KIND_ORDER):
        if name.startswith(k):
            return i
    return len(KIND_ORDER)


def main():
    names = []
    for line in sys.stdin:
        name = line.split("|")[0].strip()
        if name and not SKIP.match(name):
            names.append(name)
    ranked = sorted(
        names,
        key=lambda n: (
            -(parse_date(n) or datetime.min).toordinal(),
            kind_rank(n),
            n,
        ),
    )
    for n in ranked:
        dt = parse_date(n)
        print(f"{dt:%Y-%m-%d}  {n}" if dt else f"{'-':10}  {n}")


if __name__ == "__main__":
    main()
