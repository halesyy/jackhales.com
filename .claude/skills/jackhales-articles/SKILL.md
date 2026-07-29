---
name: jackhales-articles
description: Read, draft, and edit jackhales.com articles through the draft content API using the local scripts/jackhales-content command. Use when asked to write, rewrite, restructure, retitle, or improve the SEO or images of an article or draft on jackhales.com. Never use it to publish.
---

# Jack Hales Articles

Work on article drafts through the checked-in command. Do not call MongoDB, the
admin routes, or the private application directly.

## The One Rule

**You cannot publish. Only Jack can.**

The API enforces this — `status` is rejected, and published articles answer `409`
to every write — but do not go looking for a way around it. If the user asks to
publish, tell them the change is saved as a draft and that publishing happens in
`/admin`.

## Resolve The Command

```sh
JACKHALES_ROOT="${JACKHALES_ROOT:-$HOME/dev/jackhales.com}"
"$JACKHALES_ROOT/scripts/jackhales-content" status
```

`status` reports where the key resolves from and never its value. If it reports
`missing`, follow the [jackhales-api-key](../jackhales-api-key/SKILL.md) skill
first, then come back.

Read [docs/content-api.md](../../../docs/content-api.md) before the first edit of
a session. Point at a local backend with
`JACKHALES_API_BASE_URL=http://localhost:8000/api` when working against a dev
stack.

## Inspect Before Editing

```sh
scripts/jackhales-content list --status draft
scripts/jackhales-content read SLUG
scripts/jackhales-content read SLUG --raw      # raw Markdown only
scripts/jackhales-content sections SLUG
```

`sections` is the map of the article. Every id it returns can be edited on its
own. `preamble` is the text before the first heading. Repeated headings get
`-2`, `-3` suffixes. Read the section list again after any structural change,
because inserting or deleting a section shifts the numeric indexes.

## Edit The Smallest Thing That Works

Prefer, in order:

1. **One section** — `section SLUG SECTION_ID --body-file new-section.md`
2. **Exact text** — `replace SLUG --find "old phrase" --with "new phrase"`
3. **A new section** — `add-section SLUG --heading "Results" --after background`
4. **Metadata only** — `set SLUG --title … --meta-description … --hero-image …`
5. **The whole body** — `body SLUG --body-file article.md`

Only reach for step 5 when the user asked for a full rewrite. A section edit
splices just that section and leaves every other line, including its spacing,
exactly as it was. A whole-body replacement does not.

Write long content to a file and pass `--body-file`. Do not put multi-paragraph
Markdown in a shell argument.

## Plan, Then Apply

Every write command prints a JSON plan and changes nothing until `--apply` is
added:

```sh
scripts/jackhales-content section SLUG background --body-file section.md
scripts/jackhales-content section SLUG background --body-file section.md --apply
```

Show the user the plan for anything substantial before applying it. For a small
edit the user already described in detail, apply it and report what changed.

`replace` refuses an ambiguous match. If it reports several occurrences, either
make the `--find` text longer and unique, or pass `--count N` to confirm you mean
all of them.

## SEO And Images

```sh
scripts/jackhales-content set SLUG \
  --meta-title "…" --meta-description "…" \
  --keyword research --keyword engineering \
  --canonical-url https://jackhales.com/article/SLUG \
  --og-image https://jackhales.com/og/SLUG.png \
  --hero-image /images/SLUG-hero.png --hero-alt "What the image shows" --apply
```

`metaTitle` falls back to the title and `metaDescription` to the summary, so only
set them when they should differ. Image and canonical URLs must start with
`https://`, `http://` or `/`. Use `--clear-hero-image` to remove a hero image.

## Verify And Hand Back

After applying, re-read the article and confirm the change landed and nothing
else moved:

```sh
scripts/jackhales-content sections SLUG
scripts/jackhales-content read SLUG --raw
```

Report the slug, which sections changed, and the fact that it is still a draft
awaiting Jack's review in `/admin`. Never print the API key.
