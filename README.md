# jackhales.com

Jack Hales' personal site with:

- Next.js pages-directory frontend
- Tailwind CSS
- FastAPI backend
- MongoDB-backed article system
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
Markdown, individual sections, SEO fields, and images. It can never publish,
never change a published article, and never delete one. Publishing stays with the
admin session.

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
