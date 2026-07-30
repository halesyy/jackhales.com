# jackhales.com

Jack Hales' personal site with:

- Next.js pages-directory frontend
- Tailwind CSS
- FastAPI backend
- MongoDB-backed article system
- Paste-to-upload article images with a managed alt-text library
- Markdown tables with a visual table editor in `/admin`
- Full-page draft preview at real device widths
- Newsletter subscriptions with a token-based name update
- Email/password-protected `/admin` with MongoDB-backed sessions
- Docker Compose deployment behind Dokploy Traefik

## Local Development

```sh
cd frontend
npm install
npm run dev
```

```sh
cd backend
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Article pages use static generation with incremental revalidation. When the backend is running locally, build MongoDB-backed article HTML with:

```sh
cd frontend
INTERNAL_API_BASE_URL=http://localhost:8000/api npm run build
```

Existing articles are generated during the build. New articles are generated on their first request, and published changes revalidate every five minutes. Container builds use `BUILD_API_BASE_URL` as their build-time article source.

## Draft Content API

`/admin` can generate a single API key that lets a local command or agent work on
article **drafts**. Only one key exists at a time, and generating a new one
supersedes the previous one. Only the hash is stored; the key is shown once.

The key can read every article and edit drafts — title, slug, summary, raw
Markdown, individual sections, SEO fields, and images. It can upload a picture,
place it in a section, move it and re-describe it. It can never publish, never
change a published article, never delete one, and never delete from the image
library. Publishing stays with the admin session.

```sh
scripts/jackhales-content status
scripts/jackhales-content login --apply     # store the key in the macOS Keychain
scripts/jackhales-content list --status draft
scripts/jackhales-content sections a-draft
scripts/jackhales-content section a-draft background --body-file section.md --apply
```

Write commands print a JSON plan and change nothing until `--apply` is added.
Point at a local backend with `JACKHALES_API_BASE_URL=http://localhost:8000/api`.

See [docs/content-api.md](docs/content-api.md) for the full contract, the
guardrail table, and the TypeScript definitions. The same operations are available
through Plumb as `scripts/plumb services jackhales …`, and the `/jackhales` skill
drives that adapter.

## Draft Preview

**Preview** in the editor opens `/admin/preview` in its own tab, showing the
article exactly as a reader would see it — including edits that have not been
saved yet. The draft travels through `localStorage` rather than the URL, so an
unpublished article never reaches browser history or a server log. Pressing
Preview again updates the tab that is already open instead of piling up new ones.

The article is rendered by `ArticleView`, the same component the published page
uses, so the preview cannot drift from production. It sits inside an iframe so
the Desktop/Tablet/Phone widths are real viewports and the site's own breakpoints
actually fire — a width-constrained `div` would show desktop styling at phone
width and quietly lie about the thing most worth checking.

The bar also carries a search-result preview with title and description length
guidance, from the same fallbacks the live page uses. `/admin` and everything
under it is `Disallow`ed in `robots.txt`, and the preview page sends
`noindex, nofollow`.

## Images

Paste or drop an image into the editor's Markdown box and it is resized to at
most 1800px wide, re-encoded as WebP in the browser, uploaded, and inserted as
ordinary Markdown — a 3 MB pasted screenshot lands as roughly 20 KB. Animated
GIFs are sent through untouched so they keep moving.

Images are content addressed: the id is a digest of the bytes, so the same
picture pasted twice is stored once and every URL is immutable and cached for a
year. Uploaded URLs carry the dimensions (`?w=1800&h=1013`) so a figure reserves
its space before the bytes arrive.

The **Images** block under the editor lists everything stored, with the alt text
kept next to the picture it describes — set it once and every later insert of
that image starts out described. An image can be inserted, copied, made the hero
image, or removed; removal is refused while any article still references it.

An agent works the same library through the draft API. `body-images` maps the
pictures in an article the way `sections` maps its prose, and each one can be
placed, moved between sections, re-described or removed on its own without
rewriting the surrounding text:

```sh
scripts/jackhales-content upload-image chart.png --alt "Revenue by region" --apply
scripts/jackhales-content add-image a-draft URL --section results --at start --apply
scripts/jackhales-content move-image a-draft IMAGE_ID --section background --apply
```

Uploads are admin-only and bounded: 8 MB per image, PNG/JPEG/GIF/WebP only
(sniffed from the bytes, never from the declared content type), and a library
ceiling set by `IMAGE_STORAGE_MAX_BYTES` (256 MB by default) so images cannot
fill the MongoDB volume. `PUBLIC_API_URL` is the single place image URLs are
built from.

Add a caption with Markdown's image title, which renders as a `<figcaption>`:

```markdown
![A revenue chart](https://api.jackhales.com/api/images/70486bca…?w=1800&h=1013 "Revenue by region, FY2026")
```

## Tables

Article tables are plain GitHub-flavoured Markdown. On the frontend they render
into a rounded, scrollable panel that never pushes the page sideways — a wide
table scrolls inside its own box, down to a 320px viewport. `:---`, `:---:` and
`---:` alignment is honoured, and a column whose every value is a number is
right-aligned automatically so the digits line up.

The editor's table button opens a grid over whichever table the cursor is in, or
builds a new one: edit cells, add and remove rows and columns, set per-column
alignment, and see the Markdown it will write before applying. It writes back
padded GFM, so a table built there can still be edited by hand or by the content
API afterwards.

## Newsletter

A subscribe card sits at the bottom of every page for short updates and a note
when a new article goes up. Subscribing stores the address in the `subscribers`
collection with the client IP, the page they signed up from, and a `createdUnix`
timestamp, then returns a token once.

That token — and nothing else — lets the subscriber add their name afterwards, so
the form never blocks on it:

```sh
curl -X PATCH https://api.jackhales.com/api/subscribers/me \
  -H 'content-type: application/json' \
  -H 'x-subscriber-token: jhs_live_…' \
  -d '{"name":"A Reader"}'
```

Only the token's hash is stored. Subscribing again with an address already on the
list rotates the token rather than reporting that it is already there, so the
endpoint never confirms who is on the list. `/admin` shows the subscriber count
alongside every email, name, signup date, source and IP.

See [docs/newsletter.md](docs/newsletter.md) for the full contract and the
guardrail table.

## Deployment

GitHub Actions builds frontend and backend images and pushes them to GHCR.

The Sydney host also runs a pull-based systemd deploy timer. It pulls `main` from the public repository and runs:

```sh
IMAGE_TAG=local docker compose up -d --build --remove-orphans
```

The remote host owns runtime secrets in `/srv/apps/jackhales-testing/.env`. The existing server-side project identifier remains `jackhales-testing` so its MongoDB storage, private network, and deployment timer do not need a destructive rename during the public-domain migration.

Production routing uses `jackhales.com` and `www.jackhales.com` for Next.js, with `www` redirected to the apex domain. `api.jackhales.com` routes to FastAPI. Traefik terminates TLS for all three hostnames with the shared `letsencrypt` certificate resolver.

On a fresh deployment, `/admin` offers one-time account setup for `me@jackhales.com`. Passwords are stored as salted scrypt hashes; the plaintext password is never stored.
