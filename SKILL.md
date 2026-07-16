---
name: knowledge-sources
description: Manages named knowledge sources (packages of trusted domains + search instructions) and scopes web searches to them. USE THIS SKILL whenever the user types "/knowledge-sources" — the slash command is the primary trigger. It may be followed by + mentions to activate one or several sources for the rest of the conversation (e.g. "/knowledge-sources +Spain +EU Case Law"), or by a subcommand: list, catalog, add, edit, delete, import, learn, export, monitor, status, clear, or a scoped question. Once sources have been activated this way, keep applying them to later searches in the conversation and honour follow-up + mentions without requiring the slash command again. Do not trigger on generic web-search requests when the skill has not been invoked and no source is active.
---

# Knowledge Sources

A knowledge source is a named package of **domains** (where to search) and **instructions** (how to search and cite). When the user activates one or more sources, every web search is restricted to the union of their domains and follows the union of their instructions. No source active ⇒ normal, unrestricted behaviour (search stays opt-in).

## Data files

Both files live next to this SKILL.md:

- `data/defaults.json` — the **catalog**: 94 curated built-in sources (legal/regulatory, by jurisdiction and topic). **Read-only: never edit this file.** Catalog entries are browsable and importable but are NOT active sources by themselves.
- `data/sources.json` — the user's own sources: the only ones that `list` shows as theirs and the only file add/edit/delete/learn modify. **A fresh install ships this file empty (`[]`)** — if it is ever missing, create it with `[]` and continue. The user populates it by importing from the catalog or creating sources.

Entry schema (`type` and `aliases` only in sources.json; `search_notes` in both — the catalog ships verified notes, `learn` maintains the user's copy; `region` only in defaults.json; `last_verified` in both — in the catalog it records when the maintainer last checked the entry, in a user source it records when `learn` last built or refreshed its `search_notes`):

```json
{
  "name": "EU Case Law",
  "description": "CJEU rulings",
  "type": "caselaw",
  "aliases": ["eu", "cjeu"],
  "urls": ["curia.europa.eu"],
  "instructions": ["Prefer CJEU rulings"],
  "search_notes": ["curia.europa.eu: use the case-number search at curia.europa.eu/juris — site search is weak"]
}
```

`instructions` say **what to look for and how to cite**; `search_notes` say **how to physically reach and query the source**: per-domain access quirks ("broken TLS chain — WebFetch fails, use browser automation directly"), known-good query-interface URLs, snippet reliability, query formulations that work. `search_notes` is optional and is the field the `learn` operation maintains.

`type` must be one of: `legislation` (statutes, gazettes, supervisory bodies) · `caselaw` (courts, tribunals, administrative rulings) · `news` (specialised press, alerts, newsletters) · `web` (a curated set of concrete pages) · `research` (doctrine, papers, working documents) · `mixed` (a combination).

Constraints: `name` required and unique; `type` required; `aliases` optional, short, and unique across all sources; no `name` or `alias` may be a reserved word (case-insensitively): `web`, `all`, a region name, or a subcommand name (`list`, `catalog`, `import`, `add`, `edit`, `delete`, `learn`, `export`, `monitor`, `status`, `clear`) — these are command tokens and would make `+` mentions ambiguous; max 50 each of `urls`, `instructions` and `search_notes` per source; `urls` are bare domains — no protocol, no path (`curia.europa.eu`, not `https://curia.europa.eu/en`). `search_notes` entries may contain full URLs (they point at query interfaces, not search scopes). In defaults.json every entry also carries `region`, one of: `Global` · `Europe` · `Americas` · `Asia-Pacific` · `Middle East & Africa` — used only for catalog navigation: catalog-only, never a search scope, and dropped on import. `last_verified` is an ISO date (`YYYY-MM-DD`): in defaults.json it is required and records when the maintainer last checked the entry's URLs and notes; in sources.json it is optional, maintained by `learn`, and records when the source's `search_notes` were last built or refreshed — a source older than six months, or with no `last_verified` at all, is flagged stale by `list`/`status` and by `validate.py`. These constraints are executable: `validate.py` (Python 3, standard library) checks them — see **Validation** below.

## Validation

The constraints above are enforced in code by `validate.py` at the skill root (Python 3, standard library, zero dependencies). It checks both data files — bare-domain URLs, the `type` enum, reserved words, unique names/aliases, the 50-item caps, ISO `last_verified`, catalog `region` — and flags stale sources. Run `python3 validate.py` (both files) or `python3 validate.py data/sources.json` (one file); it prints `ERROR`/`WARN` lines and exits non-zero if any ERROR.

**Auto-gate (Claude Code): every operation that writes `data/sources.json` — add, edit, delete, import, learn — must run `python3 validate.py` immediately after the write and surface the result. If it reports an ERROR, restore the previous file content and tell the user, rather than leaving an invalid file in place.** On claude.ai the skill files are read-only and scripts do not run, so validation there is best-effort against the prose rules — the user can run `validate.py` locally on the exported `sources.json`.

## Activation flow (the primary usage)

The user types `/knowledge-sources` followed by `+` mentions to activate sources:

```
/knowledge-sources +spain +eu ¿novedades en operaciones vinculadas?
```

The mention marker is `+`, in every environment. Bare names with no marker also resolve when unambiguous (`/knowledge-sources spain, tax news`).

1. Resolve each mention (see below).
2. Confirm activation by listing the active set: each source's name, type, and domain count, plus the merged totals.
3. If the same message also contains a question, answer it immediately with the scoped search.
4. **The active set persists for the rest of the conversation**: apply it to every subsequent web search, and keep honouring `+` mentions in later messages without requiring `/knowledge-sources` again.
5. `/knowledge-sources clear` (or `+web` / "search the open web") deactivates everything — `+web` is exclusive: it clears all scoped sources and returns to unrestricted search. `/knowledge-sources status` shows the current active set, with the same `[stale]`/`[never verified]` freshness markers as `list`.

Activation works with the user's sources (`sources.json`). If a mention only matches a catalog entry, offer to import it first — importing and activating in one step is fine if the user agrees.

## Resolving source references

Match mentions case-insensitively, checking in order: exact alias → exact name → unique substring of a name.

- Exactly one match → use it.
- Several matches → list the candidates and ask which one.
- No match (or a bare `+`) → show the available names (user sources first, then catalog regions) so the user can pick. Never silently fall back to unrestricted search.

## Operations

### list — `/knowledge-sources list` (or just `/knowledge-sources`)

Show the user's sources: name, aliases, type, domain count, description, and freshness — each source's `last_verified` with a `[stale]` marker when it is older than six months and `[never verified]` when it is absent, nudging `learn +name` to refresh. If `sources.json` is empty, say so and point to `catalog` — do not dump the catalog unasked.

### catalog — `/knowledge-sources catalog [filter]`

Browse the built-in defaults without importing them:

- No filter → the regions (`region` field: Global, Europe, Americas, Asia-Pacific, Middle East & Africa) with entry counts, plus a hint to filter.
- With a filter (`catalog spain`, `catalog +tax`) → matching entries: name, domain count, description.
- Exactly one match → the full entry (all domains and instructions), plus the offer to import it.

### import — `/knowledge-sources import <names | region | all>`

Download catalog entries into `sources.json` so they become the user's own: named entries, a whole region ("import europe"), or everything. Imported entries keep the catalog's `search_notes` and carry over its `last_verified` as the freshness baseline (drop `region`); they get `"type": "mixed"` unless the content clearly maps to another type; suggest 1–2 short aliases per import and include them if the user agrees. Skip (and report) names that already exist in sources.json.

### search (the core operation)

With one or more sources active:

1. Merge: `allowed_domains` = deduplicated union of all active sources' `urls`; active instructions = deduplicated union of their `instructions`; active search notes = deduplicated union of their `search_notes`. Read the search notes **before** searching — they may short-circuit the retrieval ladder below (e.g. "petete: skip WebFetch, go straight to browser automation").
2. Run every web search for the request with `allowed_domains` set to that union. Do not mix in unrestricted searches unless the user asks. **Scoping is by domain suffix**: a listed domain covers its subdomains too (verified — `allowed_domains: ["hacienda.gob.es"]` returns `petete.tributos.hacienda.gob.es`; `["europa.eu"]` returns both `eur-lex.europa.eu` and `curia.europa.eu`). This is why a source lists the bare registrable domain when it wants the whole host tree (`boe.es`), but a specific subdomain when it wants only that slice of a broader host (`eur-lex.europa.eu`, not all of `europa.eu`) — content on a subdomain of a listed domain needs no separate entry.
3. Follow the active instructions when searching, selecting, and citing results, and apply the **Citations** rules below to the answer.
4. In the answer, state which sources scoped the search.
5. If a scoped search returns nothing useful, say so and ask whether to widen the scope; do not silently drop the restriction.

With a very large active union (e.g. after `import all`, hundreds of domains), prefer activating the specific subset relevant to the question: oversized domain whitelists dilute relevance and can degrade the web-search tool.

**Retrieval ladder** — how to get from a scoped search to a citable document:

1. Scoped web search (`allowed_domains` union) to locate candidate documents.
2. Open each candidate you intend to rely on (WebFetch) and verify it before citing. Search-result snippets are never enough.
3. If fetching fails (TLS errors, JavaScript-only application) or returns unusable content, go **directly** to browser automation against the source's query interface — do not burn attempts reverse-engineering POST endpoints with curl.
4. For long documents, navigate by page/section instead of one truncated full-text grab.

### monitor — `/knowledge-sources monitor [+sources] <period> <topic>`

The time-bound variant of search: report what the sources published on a topic within a period. Examples: `monitor último mes precios de transferencia`, `monitor +spain +eu Q2 2026 Pillar Two`.

1. **Sources**: the mentions in the command or, failing that, the active set; none → resolve as usual (show the picker; never fall back to open web silently). **Period and topic are both required** — if either is missing, ask for it.
2. **Period**: convert relative expressions to absolute dates ("último mes" → an explicit range against today's date) and state the covered range in the answer.
3. **Search**: scoped searches (merged domains) combining the topic with novelty and period terms; run several angles when the topic warrants it (new legislation, administrative doctrine, case law). Instructions, search notes, and the retrieval ladder apply as in search.
4. **Hard date filter**: verify each item's publication date in the opened document — never from a snippet — and include it only if it falls inside the range. Anything undatable with certainty is excluded or explicitly flagged as unverified.
5. **Output**: a chronological list — date · identifier with inline citation (Citations rules) · what changed and why it matters in 1–2 lines — plus the covered range and the scoping sources. If there is nothing new, say so; do not pad. The post-search learn offer applies as usual.

### add — `/knowledge-sources add ...`

- **Explicit**: the user supplies the fields → validate and save.
- **Assisted**: the user gives a free-text description ("una fuente para fiscalidad alemana con los tribunales y el ministerio") → propose a complete entry (name, aliases, description, type, domains, instructions) and **show it for confirmation before saving**.

Validate against the constraints (normalise domains by stripping protocol and path; reject duplicate names/aliases), then append to `data/sources.json`.

**After saving, always offer a proactive `learn`.** A freshly added source has empty `search_notes` and untested `instructions`, so its first real searches pay the cost of discovering each domain from scratch. Close the `add` by proposing, in the user's own terms, to run it: `/knowledge-sources learn +<name>` — probe every domain now and build the retrieval knowledge before first use (the proactive mode described under `learn`). One short offer; if declined, drop it.

### edit — `/knowledge-sources edit +<name> [changes]`

Conversational, not a form protocol. Resolve the source in `sources.json` (catalog entries cannot be edited — offer `import` first).

- **`edit +spain` with no changes** → show the full current entry, then ask what to change in plain language.
- **Changes in the same message** → apply them directly. The user describes changes naturally, in any mix: "quita cnmc.es, añade bde.es, tipo legislation, alias es", "reescribe las instrucciones para priorizar consultas vinculantes", "renómbrala a Spain Tax". Interpret, apply, and enforce the same validation as `add`.

Always close the same way: a compact **before → after diff of only the touched fields**, then **confirm before saving**. Nothing is written until the user confirms. If the source is in the active set, the changes apply from the next search.

### learn — `/knowledge-sources learn [+<name>]`

Turn search experience into persistent retrieval knowledge — the feedback loop that makes the next search start where the last one ended. It serves three occasions with one verb: the **initial setup** of a just-added source, a deliberate **review** of a source from scratch, and the **capture** of friction right after a search that hit it. Two modes, chosen by the situation:

**Reactive** — the default when the source has already been searched this conversation. Review the searches that involved it (no mention → all active sources): what failed (unreachable fetches, misleading snippets, dead-end query attempts), what finally worked (access paths, query-interface URLs, query formulations), and draft new or updated `search_notes` from it. Two triggers:

- *Automatic offer*: at the end of a scoped answer where notable friction occurred (failed fetches, snippet detours, fallback to browser automation), briefly offer 1–3 concrete learnings — "I learned X about searching this source — save it to its search_notes?". One short offer, not a lecture; if the user declines or ignores it, drop it.
- *On demand*: `learn +name` distils the same from the conversation so far.

**Proactive** — a full probe for a fresh source or a from-scratch review; this is the mode `add` offers on a new source. Don't wait for a real question. For **each domain** in the source:

1. Run a scoped web search (that domain only) for a few representative queries on the source's subject, to find where the content actually lives — hubs, listing/index pages, URL patterns, recurring digests.
2. WebFetch a representative page and observe: server-rendered vs JavaScript-only shell, cookie/WAF walls, HTML vs PDF delivery, working query-interface or index URLs, and content-bearing subdomains (the bare-domain scope already covers them — note them, don't add them as domains).
3. Record retrieval traps: multi-jurisdiction domains that mix other countries' content on the same host, hubs that return empty results to a plain fetch, path prefixes that isolate the wanted content.

Draft one `search_notes` entry per domain plus any cross-cutting note. This mode is heavier — it fetches every domain; for a very large domain list, probe the highest-value domains and say which were sampled rather than fetching all.

Common to both modes:

- **Consent is mandatory.** Same closing as `edit`: a before → after diff of the touched fields, and nothing is written until the user confirms.
- **Freshness stamp.** When a run writes or refreshes a source's `search_notes`, set its `last_verified` to today (shown in the diff). This is what clears the `[stale]`/`[never verified]` flag in `list`/`status`.
- **Deduplicate**: merge with existing notes instead of appending near-duplicates; when a learning refines an existing note, propose rewording it.
- **Source-specific only**: generic lessons (e.g. "verify before citing") are already codified in the retrieval ladder and Citations sections — say so rather than pollute a source with them.
- **`search_notes` is the primary target; `instructions` only in a proactive review.** Reactive learn touches `search_notes` only. A proactive probe may additionally propose `instructions` changes when the recon exposes a systematic gap — several domains needing the same jurisdiction filter, a recurring digest that is the efficient entry point for period sweeps — shown in the same diff. For any other `instructions` edit, use `edit`.

### export — `/knowledge-sources export [path]`

Back up or migrate the user's sources: deliver a copy of the current `data/sources.json` (after any pending in-memory changes on claude.ai).

- **Claude Code**: write it to the path the user gives; with no path, save `knowledge-sources-export-<YYYY-MM-DD>.json` in the current working directory and send it to the user.
- **claude.ai**: output it as a downloadable file (same mechanism as the read-only edit flow).

Export is read-only with respect to `data/sources.json` — it never modifies the skill's data. To restore on another install, the exported file simply replaces `data/sources.json`.

### delete — `/knowledge-sources delete +<name>`

Resolve the source in `sources.json`, show name + domain count, and **confirm before deleting**. Catalog entries cannot be deleted.

## Citations

Applies to every answer produced from a scoped search:

- **Inline, claim-level.** Every legal or factual statement carries its citation in the same sentence — document identifier plus link: consulta number for DGT ("DGT V0213-21, de 9-2-2021"), ECLI for judgments, official-gazette consolidated reference for provisions. The reader must never need a footnote section to know why a sentence says what it says.
- **Verified-only.** Cite only documents actually opened and read (fetched or via browser). A search-engine snippet is never sufficient support for a claim — snippets misattribute numbers and dates. If something could not be verified in full text, say so explicitly instead of citing it.
- **Pinpoint** when the claim rests on specific wording: fundamento, apartado, or article, with a brief quoted fragment where decisive.
- **Source instructions specialise the format.** The active sources' `instructions` (citation conventions, authority classification) take precedence over these defaults; this section is the floor.
- Close with a supplementary **sources-consulted list**: identifier, date, URL, and whether the full text was verified. It complements the inline citations — it never replaces them.

## Environment differences

- **Claude Code**: read and write the data files directly with file tools. Paths are relative to this skill's directory (e.g. `~/.claude/skills/knowledge-sources/data/sources.json`).
- **claude.ai**: skill files are read-only. Perform add/edit/delete/import/learn in memory, then output the complete updated `sources.json` as a downloadable file and tell the user to replace `data/sources.json` in the skill folder and re-upload the skill. Scoped search works exactly the same (use the web search tool's allowed-domains capability).
