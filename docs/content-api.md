# Draft Content API

Status: `1.0`

The content API lets a local command or agent work on **drafts** of jackhales.com
articles. It is authenticated by a single API key generated in `/admin`.

Publishing is deliberately not part of this surface. Only the admin session can
change an article's status, and a published article is read-only to every API key.

## The Key

- Exactly one key exists at a time. It lives in MongoDB as `apiKeys._id: "active"`.
- Generating a new key in `/admin` **supersedes** the previous one immediately.
- Only an HMAC-SHA256 hash is stored. The plaintext is shown once, at generation.
- The key is presented as `Authorization: Bearer <key>` or `X-API-Key: <key>`.
  It is never accepted from a query string.
- Format: `jhk_live_<43 url-safe characters>`. Only the last six are ever displayed again.

```sh
scripts/jackhales-content status      # where the key resolves from, never its value
scripts/jackhales-content login --apply   # store it in the macOS Keychain
scripts/jackhales-content whoami      # ask the API what this key may do
```

## Guardrails

| Guardrail | Behaviour |
| --- | --- |
| Publication state | `status`, `publish`, `published`, `publishedState` are rejected by the request model with `422` |
| AI attribution | `aiAssisted` is rejected with `422` and set to `true` by the API on every key-authenticated write |
| Published articles | Every write route returns `409` and changes nothing |
| Unknown fields | Rejected (`extra="forbid"`) rather than silently ignored |
| Deletion | Articles cannot be deleted; only sections within a draft can |
| Admin routes | `/api/admin/*` never accepts an API key — it requires the admin session cookie |
| Image and canonical URLs | Must start with `https://`, `http://` or `/` |
| Ambiguous text replacement | Refused unless `expectedCount` confirms the number of matches |
| Failed edits | Validated before the write, so a rejected edit leaves the draft untouched |

## Endpoints

All paths are relative to `https://api.jackhales.com/api`.

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/content/whoami` | Scope, label, and the explicit list of what the key cannot do |
| `GET` | `/content/articles` | List articles; `?status=draft` or `?status=published` |
| `GET` | `/content/articles/{slug}` | Read one article, including the raw `bodyMarkdown` |
| `POST` | `/content/articles` | Create a draft (`status` is always `draft`) |
| `PATCH` | `/content/articles/{slug}` | Update title, slug, summary, `publishedAt`, `seo`, `heroImage` |
| `PUT` | `/content/articles/{slug}/body` | Replace the whole raw Markdown body |
| `POST` | `/content/articles/{slug}/body/replace` | Exact text replacement with an occurrence guard |
| `GET` | `/content/articles/{slug}/sections` | List addressable sections |
| `PUT` | `/content/articles/{slug}/sections/{sectionId}` | Rewrite one section's heading and/or body |
| `POST` | `/content/articles/{slug}/sections` | Insert a section `after` or `before` another |
| `DELETE` | `/content/articles/{slug}/sections/{sectionId}` | Remove one section |

Reads cover published articles too, so an agent can use live work as context.
Writes are refused on anything that is not a draft.

## Sections

Sections are how an article is edited without rewriting it. The body is split on
ATX headings, ignoring any heading inside a fenced code block. Each section gets a
stable id from its heading anchor, with `-2`, `-3` suffixes for repeated headings.
Text before the first heading is addressable as `preamble`. Sections can also be
addressed by their numeric index.

```json
{
  "slug": "a-draft",
  "status": "draft",
  "editable": true,
  "sections": [
    { "id": "preamble", "index": 0, "level": 0, "heading": "", "body": "…", "characters": 42, "words": 7 },
    { "id": "background", "index": 1, "level": 2, "heading": "Background", "body": "…", "characters": 310, "words": 52 }
  ]
}
```

A section edit splices only that section's lines. Every other line of the article,
including its blank-line spacing, is preserved byte for byte.

## Article Fields

```jsonc
{
  "title": "…",
  "slug": "a-draft",
  "summary": "…",
  "bodyMarkdown": "…",
  "publishedAt": "2026-07-29T00:00:00Z",
  "status": "draft",              // read-only for API keys
  "aiAssisted": true,             // set by the API on every key write; not settable by a key
  "seo": {
    "metaTitle": null,            // falls back to the title
    "metaDescription": null,      // falls back to the summary
    "canonicalUrl": null,
    "keywords": [],
    "ogImageUrl": null,
    "noIndex": false
  },
  "heroImage": { "url": "/images/hero.png", "alt": "…", "caption": "" }
}
```

`PATCH` accepts `clearHeroImage: true` to remove the hero image.

## AI Attribution

Any write made with an API key sets `aiAssisted` to `true` on that article. The
site renders it as an AI-assisted badge linking to
[`/ai-assisted`](https://jackhales.com/ai-assisted), which explains that the
direction, research and conclusions are Jack's and that AI helped with drafting
and structuring.

A key cannot send `aiAssisted` in either direction — attempting it is a `422`.
Only the admin form can clear the flag, so assistance cannot quietly go
unrecorded.

## Type Definitions

- Python (authoritative): [`backend/app/schemas.py`](../backend/app/schemas.py)
- TypeScript for the site: [`frontend/lib/types.ts`](../frontend/lib/types.ts)
- TypeScript for external consumers: [`docs/content-api.d.ts`](./content-api.d.ts)
- Generated OpenAPI: `https://api.jackhales.com/openapi.json`

## Local Command

`scripts/jackhales-content` needs no dependencies beyond Python 3.9+. Write
commands print a JSON plan and only change anything with `--apply`.

```sh
scripts/jackhales-content list --status draft
scripts/jackhales-content read a-draft --raw
scripts/jackhales-content sections a-draft
scripts/jackhales-content new "A new piece" --summary "What it covers"
scripts/jackhales-content new "A new piece" --summary "What it covers" --apply
scripts/jackhales-content set a-draft --meta-title "…" --hero-image /images/hero.png --apply
scripts/jackhales-content section a-draft background --body-file section.md --apply
scripts/jackhales-content replace a-draft --find "old phrase" --with "new phrase" --apply
scripts/jackhales-content add-section a-draft --heading "Results" --after background --apply
```

Point it at a local backend with `JACKHALES_API_BASE_URL=http://localhost:8000/api`.

The same operations are available through Plumb as `scripts/plumb services
jackhales …`, which is the route to use when the key is held in Plumb's
credential store.
