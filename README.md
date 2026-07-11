# jackhales.jackhalestesting.xyz

Minimal test rebuild of `jackhales.com` with:

- Next.js pages-directory frontend
- Tailwind CSS
- FastAPI backend
- MongoDB-backed article system
- PIN-protected `/admin`
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

The remote host owns runtime secrets in `/srv/apps/jackhales-testing/.env`.
