# jackhales.com

Jack Hales' personal site with:

- Next.js pages-directory frontend
- Tailwind CSS
- FastAPI backend
- MongoDB-backed article system
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

## Deployment

GitHub Actions builds frontend and backend images and pushes them to GHCR.

The Sydney host also runs a pull-based systemd deploy timer. It pulls `main` from the public repository and runs:

```sh
IMAGE_TAG=local docker compose up -d --build --remove-orphans
```

The remote host owns runtime secrets in `/srv/apps/jackhales-testing/.env`. The existing server-side project identifier remains `jackhales-testing` so its MongoDB storage, private network, and deployment timer do not need a destructive rename during the public-domain migration.

Production routing uses `jackhales.com` and `www.jackhales.com` for Next.js, with `www` redirected to the apex domain. `api.jackhales.com` routes to FastAPI. Traefik terminates TLS for all three hostnames with the shared `letsencrypt` certificate resolver.

On a fresh deployment, `/admin` offers one-time account setup for `me@jackhales.com`. Passwords are stored as salted scrypt hashes; the plaintext password is never stored.
