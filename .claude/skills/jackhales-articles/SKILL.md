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

## Every Edit Is Disclosed

Any write you make sets `aiAssisted` on that article, and the site renders an
AI-assisted badge linking to `/ai-assisted`. The field is refused in both
directions, so it can be neither claimed nor suppressed. Say so when you first
mark an article that was not previously marked, and never try to remove it.

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

## Images In The Body

**You cannot upload an image.** Uploading is admin-only, so a picture enters the
library only when Jack pastes or drops one into the editor. Never invent an image
URL — a guessed one renders as a broken image on a published page.

Use a URL that already appears in an article (`read SLUG --raw`), a file the site
already ships such as `/oman.jpeg`, or one Jack gives you after pasting the image
into `/admin`. If a section needs a picture that does not exist yet, write the
section without it and tell Jack what to paste and where.

```markdown
![A revenue chart broken down by region](https://api.jackhales.com/api/images/70486bca…?w=1800&h=1013 "Revenue by region, FY2026")
```

- The alt text describes the image for someone who cannot see it — a sentence
  about the content, not "image of a chart". Only a decorative image gets `![]`.
- The optional title renders as a visible caption under the image.
- An image alone on its line becomes a figure; inside a sentence it stays inline.
- Uploaded URLs carry `?w=…&h=…`. **Keep them.** They are the real dimensions and
  let the page reserve space; stripping them makes the article jump as it loads.
- The id is a digest of the bytes, so a URL never changes meaning and the same
  one can be reused across articles.

## Tables In The Body

Plain GitHub-flavoured Markdown — there is no custom syntax. The site renders a
table into a panel that scrolls inside its own box, so a wide one never pushes
the page sideways.

```markdown
| Region | Revenue | Growth | Notes             |
| ------ | ------: | :----: | ----------------- |
| Sydney | 1,200   | 12%    | Strongest quarter |
| Perth  | 940     | 4%     | Flat on last year |
```

- `:---` left, `:---:` centre, `---:` right.
- A column whose every value is a number is right-aligned automatically —
  currency symbols, thousands separators and percentages count. Declare an
  alignment on a numeric column only to override that.
- The header row is required. A literal pipe in a cell must be escaped as `\|`.
- Cells take inline Markdown — bold, links, code — but not lists or paragraphs.
- GFM has no table caption; put a short italic line underneath if one is needed.
- Keep to roughly six columns. Past that a reader scrolls more than they read.

Pad the columns as shown. `/admin` has a visual table editor that writes padded
GFM, so matching it keeps a later round trip through that grid from producing a
diff that is all whitespace.

## Verify And Hand Back

After applying, re-read the article and confirm the change landed and nothing
else moved:

```sh
scripts/jackhales-content sections SLUG
scripts/jackhales-content read SLUG --raw
```

Report the slug, which sections changed, and the fact that it is still a draft
awaiting Jack's review in `/admin`. Never print the API key.
