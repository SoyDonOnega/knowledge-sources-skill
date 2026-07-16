# Knowledge Sources — Agent Skill for Claude

Scope Claude's web searches to the sources you trust — and get answers that cite their evidence, line by line.

A **knowledge source** is a named package of trusted domains plus instructions on how to search and cite them. Activate one or more sources and every web search in the conversation is restricted to the union of their domains, follows their instructions, and produces answers with claim-level inline citations to documents that were actually opened and read — never to a search snippet. Works in **Claude Code** and **claude.ai**.

> **Not just for legal work.** The skill and its built-in catalog are built around legal and regulatory research, but the mechanism — scope searches to domains you trust, follow per-source instructions, cite only what was opened — is domain-agnostic. It is just as useful for any field where you want to search a curated set of sources instead of the open web: medical and scientific literature, finance and markets, engineering docs, standards bodies, a company's own knowledge base. Bring your own domains with `add` and `import`.

## What it guarantees — and what it doesn't

The skill is precise about the difference between a *mechanism* it enforces and a *starting point* it gives you.

**Enforced on every scoped answer:**

- **Scoped search.** Web search runs only against the union of the active sources' domains. If a scoped search returns nothing, the skill says so and asks before widening — it never silently drops the restriction.
- **Verified-only citation.** A claim is cited only from a document that was actually opened and read (fetched or via browser automation). Search-engine snippets are never sufficient support; anything that could not be verified in full text is flagged as such, not cited.
- **Consent before writing.** Every operation that changes your sources (`add`, `edit`, `delete`, `import`, `learn`) shows a diff and waits for your confirmation before saving.
- **Schema validation.** `validate.py` checks the data files against the schema and, in Claude Code, runs automatically after each write to your sources.

**Provided as a head start, not a guarantee:** the built-in catalog. Its domains, `instructions` and `search_notes` are *curated* entry points for each jurisdiction — a place to start, not a verified oracle. `search_notes` in particular are best-effort retrieval hints that `learn` refines from your own real searches, and `last_verified` tells you how fresh each entry's notes are. See [The catalog](#the-catalog) for the honest version.

## Why

- **Precision** — research runs only against domains you chose (official gazettes, courts, regulators, journals), not whatever ranks first.
- **Verifiability** — every claim carries its citation in the same sentence, and nothing is cited from a snippet — only from documents actually opened.
- **Memory** — the skill learns how to search each source (access quirks, working query interfaces) and, with your approval, saves it for next time — both up front when you add a source and afterwards from real searches.
- **Portability** — everything is plain JSON in a git repo; your sources travel with you and are trivial to back up, version, and share.

## Quick start

### Claude Code

```sh
git clone https://github.com/SoyDonOnega/knowledge-sources-skill.git
ln -s "$(pwd)/knowledge-sources-skill" ~/.claude/skills/knowledge-sources
```

Then, in any conversation:

```
/knowledge-sources import spain          # pull curated entries from the catalog
/knowledge-sources +spain <your question>
```

### claude.ai

Zip the folder and upload it as a skill (Settings → Capabilities → Skills):

```sh
cd knowledge-sources-skill
zip -r knowledge-sources.zip . -x '.git/*' -x 'knowledge-sources.zip'
```

On claude.ai the skill files are read-only: when you change your sources there, the skill returns the updated `sources.json` as a downloadable file — save it into this folder and re-upload. `validate.py` does not run on claude.ai; run it locally against the exported `sources.json` if you want the schema check.

## How it works

1. **Activate** sources with `+` mentions: `/knowledge-sources +spain +eu`. The active set persists for the whole conversation; later `+name` mentions keep working without repeating the command. `clear` or `+web` returns to unrestricted search.
2. **Search** runs with the merged domain whitelist of all active sources and applies their instructions. If a scoped search finds nothing, the skill says so and asks before widening — it never silently drops your restriction.
3. **Cite** — answers reference, in the text, why they say what they say: document identifier plus link in the same sentence, pinpoint references (article, paragraph) where wording matters, and a closing list of sources consulted with each item's verification status.
4. **Monitor** — `/knowledge-sources monitor <period> <topic>` reports what the active sources published on a topic within a period: relative periods are converted to explicit date ranges, every item's publication date is verified in the opened document (never taken from a snippet), and the output is a chronological, cited list — or an honest "nothing new".
5. **Learn** — the single verb that builds and maintains a source's retrieval knowledge, always with a diff and confirmation. It is **not only an after-the-session tool**: the same command does the initial **setup** of a source too. Two modes, picked by the situation:

   - *Proactive (setup / from-scratch review)* — you don't need to have searched anything yet. When you add a source, `learn` offers to probe **every** domain up front (server-rendered or JS shell? where does the content live? which paths mix in other jurisdictions?) and write the notes before your first real search, tuning `instructions` too where the recon exposes a systematic gap — so the first search starts warm instead of discovering each domain from scratch. Run it any time you want a full re-review of a source.
   - *Reactive (after searching)* — turns the friction of real searches into knowledge ("this court database rejects standard fetching — use its query interface at …") and saves it to the source's `search_notes`, offered automatically when a search hits a snag.

### A note on domain scope

`urls` are **bare registrable domains** — `boe.es`, not `https://boe.es/en`. The scope applied to a search is the deduplicated union of the active sources' domains. When a source's content actually lives on a subdomain (a court database at `hj.tribunalconstitucional.es`, a tax-ruling interface under `hacienda.gob.es`), the intent is for the bare parent domain to cover it; the entry's `search_notes` record the exact subdomain and query path to use. If a scoped search unexpectedly returns nothing for a source you know publishes on the topic, that mismatch is worth checking first — and a good prompt for `learn` to capture the working path.

## Worked example

A full pass, from an empty install to a cited answer. The legal content below is
illustrative — the point is the mechanics of each step.

**1. Import a catalog source into your own.**

```
/knowledge-sources import spain
```

> Imported **Spain** into your sources (29 domains). Suggested aliases: `es`, `spain`.
> Your sources now: Spain.

**2. Activate it and ask in the same message.**

```
/knowledge-sources +spain what is the DGT's position on the deductibility of intra-group interest?
```

> Active: **Spain** (mixed, 29 domains). Search scoped to those domains.
>
> The binding rulings of the Dirección General de Tributos treat intra-group
> interest as deductible only where … [DGT V####-##, dd-mm-yyyy], provided …
> [pinpoint to the relevant paragraph].
>
> **Sources consulted**
> - DGT V####-## — dd-mm-yyyy — petete.tributos.hacienda.gob.es/… — full text verified
>
> *Learned while searching:* the DGT consulta database rejects plain fetching —
> reached it through its query interface at petete.tributos.hacienda.gob.es. Save
> this to Spain's `search_notes`? (y/n)

Every claim carries its citation in the same sentence; the closing list marks
whether each document was opened and verified. Nothing is cited from a snippet.

**3. Keep the scope for the rest of the conversation.**

The active set persists — later questions stay scoped to Spain without repeating
the command, and a new `+eu` mention adds the EU source on top:

```
+eu and the CJEU's position?
```

**4. Time-bound sweep.**

```
/knowledge-sources monitor +spain last quarter transfer pricing
```

> Range covered: 2026-04-01 to 2026-06-30. Scoped to Spain.
> A chronological, date-verified list of what those domains published on the
> topic — or an honest "nothing new".

**5. Return to the open web** when you want unrestricted search:

```
/knowledge-sources clear
```

## Commands

| Command | What it does |
|---|---|
| `/knowledge-sources +a +b [question]` | Activate sources (aliases and partial names work) and optionally ask right away |
| `/knowledge-sources status` · `clear` | Show or reset the active set (with `[stale]` freshness flags) |
| `/knowledge-sources list` | Your sources, with per-source `[stale]`/`[never verified]` freshness flags |
| `/knowledge-sources catalog [filter]` | Browse the built-in catalog (94 curated legal and regulatory sources) |
| `/knowledge-sources import <names\|region\|all>` | Copy catalog entries into your sources |
| `/knowledge-sources add …` | Create a source, explicit or assisted from a description |
| `/knowledge-sources edit +name [changes]` | Edit conversationally; diff shown, confirmation required |
| `/knowledge-sources learn [+name]` | Persist retrieval knowledge for a source (with confirmation): reactively from this session's searches, or a proactive full-domain probe on a fresh source — offered automatically after `add` |
| `/knowledge-sources monitor [+sources] <period> <topic>` | What the sources published on a topic within a period — chronological, date-verified, cited |
| `/knowledge-sources export [path]` | Back up your `sources.json`; restore by replacing the file on another install |
| `/knowledge-sources delete +name` | Remove a source (with confirmation) |

The mention marker is `+` everywhere (Claude Code and claude.ai). Mentions resolve
case-insensitively: exact alias → exact name → unique substring of a name. An
ambiguous mention lists the candidates and asks; an unmatched one shows the
available names — it never silently falls back to the open web.

## The catalog

The skill ships with **94 curated legal and regulatory sources** — one per jurisdiction plus supranational entries — grouped into five regions:

| Region | Entries | Includes |
|---|---|---|
| Global | 3 | International (OECD, BIS, World Bank, WIPO, FATF), European Union, United Nations |
| Europe | 39 | Spain, France, Germany, Italy, UK, Netherlands, Switzerland… |
| Americas | 23 | United States, Canada, Brazil, Mexico, Argentina, Chile… |
| Asia-Pacific | 17 | Japan, China, India, Australia, Singapore, South Korea… |
| Middle East & Africa | 12 | UAE, Saudi Arabia, Israel, South Africa, Nigeria, Egypt… |

**What a catalog entry is — and is not.** Each entry is a *curated starting package*, schema-validated by `validate.py`, not a verified oracle:

- **`urls`** — the bare registrable domains of the authoritative bodies for that jurisdiction: official gazettes, courts, regulators, supervisory and registry authorities.
- **`instructions`** — what to look for in that jurisdiction and how to cite it (which identifier, which authority ranks above which).
- **`search_notes`** — best-effort retrieval hints: where the content lives, known query-interface URLs, access quirks (WAF walls, JavaScript-only shells, PDF vs HTML). Treat them as a head start, not gospel. They are refined from your own searches by `learn`, and `last_verified` records when they were last built or refreshed — a stale entry is flagged so you know to re-check before relying on it.

Every entry passes `validate.py` (bare-domain URLs, valid schema, unique names, no reserved words). Browse with `catalog [filter]`; pull entries into your own sources with `import <name | region | all>`. On import an entry becomes yours: it keeps the catalog's `search_notes` and carries over `last_verified` as the freshness baseline, drops the catalog-only `region` field, and gets a `type` and optional aliases.

## Data

```
SKILL.md              the skill (repo root = skill root)
validate.py           zero-dependency validator (Python 3 stdlib) for the data files
data/defaults.json    catalog: 94 curated built-in sources (read-only)
data/sources.json     your sources — ships empty ([]), yours from the first import
```

A source looks like this (full schema and validation rules in `SKILL.md`):

```json
{
  "name": "EU Case Law",
  "type": "caselaw",
  "aliases": ["eu", "cjeu"],
  "urls": ["curia.europa.eu"],
  "instructions": ["Cite ECLI and judgment date"],
  "search_notes": ["Use the case-number search at curia.europa.eu/juris"],
  "last_verified": "2026-01-31"
}
```

- **`name`** — required, unique, not a reserved word (`web`, `all`, a region name, or a subcommand).
- **`type`** — required in your sources: one of `legislation`, `caselaw`, `news`, `web`, `research`, `mixed`.
- **`aliases`** — optional short handles for `+` mentions; unique across all sources.
- **`urls`** — 1–50 bare domains (no scheme, no path).
- **`instructions`** — what to look for and how to cite (up to 50).
- **`search_notes`** — retrieval knowledge (access quirks, query interfaces) maintained by `learn`; may contain full query-interface URLs (up to 50).
- **`last_verified`** — ISO date; when `learn` last built or refreshed this source's `search_notes`.

## Validation & freshness

`validate.py` checks both data files against the schema — bare-domain URLs, the `type` enum, reserved words, unique names and aliases, the 50-item caps, ISO `last_verified` — prints `ERROR`/`WARN` lines, and exits non-zero on any error. Run it any time:

```sh
python3 validate.py                     # both data files
python3 validate.py data/sources.json   # one file
```

In Claude Code the skill runs it automatically after each write to your sources and restores the previous file if an error is introduced. On claude.ai scripts don't run — run `validate.py` locally on the exported `sources.json`.

**Freshness.** `last_verified` records when `learn` last built or refreshed a source's `search_notes`. Once it passes six months — or is missing entirely — `list` and `status` flag the source `[stale]` / `[never verified]`, nudging you to re-run `learn` before trusting its retrieval notes. Freshness is a signal about the *notes*, not a promise that every URL is live today; when in doubt, `learn +name` re-probes the source.

## License

MIT — see [LICENSE](LICENSE).
