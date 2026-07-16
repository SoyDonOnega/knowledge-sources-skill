#!/usr/bin/env python3
"""
validate.py — executable schema for the knowledge-sources skill.

Checks data/sources.json and data/defaults.json against the constraints
documented in SKILL.md. Prints ERROR and WARN lines; exits 1 if any ERROR,
0 otherwise. Zero dependencies (Python 3 standard library).

Usage:
    python3 validate.py                     # validate both data files
    python3 validate.py data/sources.json   # validate one file

Rules enforced (prose in SKILL.md):
  Every entry:
    - name: non-empty string; not a reserved word; unique within file (case-insensitive)
    - urls: list of 1..50 bare domains — no scheme, no path, no whitespace, must contain a dot
    - instructions / search_notes: lists of at most 50 strings each
      (search_notes may contain full URLs; urls may not)
    - description: recommended (WARN if missing)
  sources.json only:
    - type: required, one of legislation|caselaw|news|web|research|mixed
    - aliases: optional; each short, not reserved, unique across all sources,
      not colliding with any name
    - last_verified: optional ISO YYYY-MM-DD, maintained by `learn`.
      absent -> WARN "never verified"; older than STALE_DAYS -> WARN "stale"
    - region: must NOT be present (catalog-only, dropped on import) -> ERROR
  defaults.json only:
    - region: required, one of the five region names
    - last_verified: required ISO YYYY-MM-DD
    - type / aliases: not expected (sources-only) -> WARN
"""

import json
import os
import re
import sys
from datetime import date, datetime

STALE_DAYS = 183  # ~6 months

REGIONS = {"global", "europe", "americas", "asia-pacific", "middle east & africa"}
SUBCOMMANDS = {"list", "catalog", "import", "add", "edit", "delete", "learn",
               "export", "monitor", "status", "clear"}
RESERVED = {"web", "all"} | REGIONS | SUBCOMMANDS
TYPES = {"legislation", "caselaw", "news", "web", "research", "mixed"}

MAX_LIST = 50
MAX_ALIAS_LEN = 24

DOMAIN_RE = re.compile(
    r"^(?=.{1,253}$)[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?"
    r"(\.[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?)+$"
)


class Report:
    def __init__(self):
        self.errors = 0
        self.warnings = 0

    def error(self, where, msg):
        print(f"ERROR  {where}: {msg}")
        self.errors += 1

    def warn(self, where, msg):
        print(f"WARN   {where}: {msg}")
        self.warnings += 1


def parse_iso(value):
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


def check_str_list(rep, where, entry, field):
    val = entry.get(field)
    if val is None:
        return
    if not isinstance(val, list):
        rep.error(where, f"'{field}' must be a list")
        return
    if len(val) > MAX_LIST:
        rep.error(where, f"'{field}' has {len(val)} items (max {MAX_LIST})")
    for i, item in enumerate(val):
        if not isinstance(item, str) or not item.strip():
            rep.error(where, f"'{field}[{i}]' must be a non-empty string")


def check_urls(rep, where, entry):
    urls = entry.get("urls")
    if not isinstance(urls, list) or not urls:
        rep.error(where, "'urls' must be a non-empty list")
        return
    if len(urls) > MAX_LIST:
        rep.error(where, f"'urls' has {len(urls)} items (max {MAX_LIST})")
    for u in urls:
        if not isinstance(u, str):
            rep.error(where, f"url {u!r} must be a string")
            continue
        if "://" in u or "/" in u:
            rep.error(where, f"url '{u}' must be a bare domain (no scheme or path)")
            continue
        if any(c.isspace() for c in u):
            rep.error(where, f"url '{u}' contains whitespace")
            continue
        if not DOMAIN_RE.match(u.lower()):
            rep.error(where, f"url '{u}' is not a valid bare domain")
            continue
        if u != u.lower():
            rep.warn(where, f"url '{u}' should be lowercase")


def check_name(rep, where, entry, seen_names):
    name = entry.get("name")
    if not isinstance(name, str) or not name.strip():
        rep.error(where, "missing/empty 'name'")
        return None
    low = name.lower()
    if low in RESERVED:
        rep.error(where, f"name '{name}' is a reserved word")
    if low in seen_names:
        rep.error(where, f"duplicate name '{name}' (also entry {seen_names[low]})")
    else:
        seen_names[low] = where
    return name


def check_description(rep, where, entry):
    desc = entry.get("description")
    if not (isinstance(desc, str) and desc.strip()):
        rep.warn(where, "missing 'description'")


def check_last_verified(rep, where, value, stale_msg):
    d = parse_iso(value)
    if d is None:
        rep.error(where, f"last_verified '{value}' is not ISO YYYY-MM-DD")
        return
    age = (date.today() - d).days
    if age < 0:
        rep.error(where, f"last_verified '{value}' is in the future")
        return
    if age > STALE_DAYS:
        rep.warn(where, stale_msg.format(date=value, age=age))


def validate_sources(rep, entries):
    seen_names, seen_aliases = {}, {}
    names_lower = {
        e["name"].lower()
        for e in entries
        if isinstance(e.get("name"), str)
    }
    for idx, entry in enumerate(entries):
        name = entry.get("name")
        where = f"sources[{idx}] '{name}'" if isinstance(name, str) else f"sources[{idx}]"

        check_name(rep, where, entry, seen_names)
        check_description(rep, where, entry)
        check_urls(rep, where, entry)
        check_str_list(rep, where, entry, "instructions")
        check_str_list(rep, where, entry, "search_notes")

        t = entry.get("type")
        if t is None:
            rep.error(where, "missing required 'type'")
        elif t not in TYPES:
            rep.error(where, f"type '{t}' not one of {sorted(TYPES)}")

        aliases = entry.get("aliases")
        if aliases is not None:
            if not isinstance(aliases, list):
                rep.error(where, "'aliases' must be a list")
            else:
                for a in aliases:
                    if not isinstance(a, str) or not a.strip():
                        rep.error(where, f"alias {a!r} must be a non-empty string")
                        continue
                    al = a.lower()
                    if len(a) > MAX_ALIAS_LEN:
                        rep.warn(where, f"alias '{a}' is long ({len(a)} chars)")
                    if al in RESERVED:
                        rep.error(where, f"alias '{a}' is a reserved word")
                    if al in names_lower and al != (name or "").lower():
                        rep.error(where, f"alias '{a}' collides with a source name")
                    if al in seen_aliases:
                        rep.error(where, f"duplicate alias '{a}' (also {seen_aliases[al]})")
                    else:
                        seen_aliases[al] = where

        if "region" in entry:
            rep.error(where, "'region' is catalog-only; drop it from sources.json")

        lv = entry.get("last_verified")
        if lv is None:
            rep.warn(where, "never verified — run `learn +name` to build/refresh search_notes")
        else:
            check_last_verified(
                rep, where, lv,
                "stale — search_notes last verified {date} ({age} days ago); run `learn +name`",
            )


def validate_defaults(rep, entries):
    seen_names = {}
    for idx, entry in enumerate(entries):
        name = entry.get("name")
        where = f"defaults[{idx}] '{name}'" if isinstance(name, str) else f"defaults[{idx}]"

        check_name(rep, where, entry, seen_names)
        check_description(rep, where, entry)
        check_urls(rep, where, entry)
        check_str_list(rep, where, entry, "instructions")
        check_str_list(rep, where, entry, "search_notes")

        region = entry.get("region")
        if region is None:
            rep.error(where, "missing required 'region'")
        elif not isinstance(region, str) or region.lower() not in REGIONS:
            rep.error(where, f"region '{region}' is not one of the five region names")

        lv = entry.get("last_verified")
        if lv is None:
            rep.error(where, "missing required 'last_verified'")
        else:
            check_last_verified(
                rep, where, lv, "catalog entry stale — last verified {date} ({age} days ago)",
            )

        if "type" in entry:
            rep.warn(where, "'type' is sources-only; not expected in the catalog")
        if "aliases" in entry:
            rep.warn(where, "'aliases' is sources-only; not expected in the catalog")


def load(path, rep):
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        rep.error(path, "file not found")
        return None
    except json.JSONDecodeError as exc:
        rep.error(path, f"invalid JSON: {exc}")
        return None
    if not isinstance(data, list):
        rep.error(path, "top level must be a JSON array")
        return None
    return data


def main(argv):
    root = os.path.dirname(os.path.abspath(__file__))
    if len(argv) > 1:
        targets = argv[1:]
    else:
        targets = [
            os.path.join(root, "data", "sources.json"),
            os.path.join(root, "data", "defaults.json"),
        ]

    rep = Report()
    total = 0
    for path in targets:
        data = load(path, rep)
        if data is None:
            continue
        total += len(data)
        if os.path.basename(path) == "defaults.json":
            validate_defaults(rep, data)
        else:
            validate_sources(rep, data)

    print(f"\n{total} entries checked, {rep.errors} errors, {rep.warnings} warnings")
    return 1 if rep.errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
