# jackhales.com migration

This repository is prepared for the public-domain cutover, but the migration branch does not deploy itself and does not change DNS.

## Target routing

- `https://jackhales.com` -> Next.js frontend on `compute-2-sydney`
- `https://www.jackhales.com` -> permanent redirect to `https://jackhales.com`
- `https://api.jackhales.com` -> FastAPI backend on `compute-2-sydney`
- `https://jackhales.jackhalestesting.xyz` -> temporary permanent redirect to `https://jackhales.com`
- `https://jackhales.jackhalestesting.xyz/api/*` -> temporary backend compatibility route

Traefik discovers the Compose labels through its Docker provider. The existing `letsencrypt` resolver requests and renews certificates after the new names resolve to the Sydney host.

## DNS changes

The authoritative DNS zone is managed by Squarespace Domains using the existing Google Domains nameservers. Preserve the nameservers and all email records.

Create or replace only these records:

| Host | Type | Value | TTL | Action |
| --- | --- | --- | --- | --- |
| `@` | `A` | `51.161.153.238` | `300` | Replace the current Vercel value `76.76.21.21` |
| `www` | `CNAME` | `jackhales.com` | `300` | Replace `cname.vercel-dns.com` |
| `api` | `A` | `51.161.153.238` | `300` | Create |

Do not change or delete the Google Workspace MX records, SPF TXT record, domain-verification records, or nameservers. Do not add an AAAA record unless IPv6 is separately configured and verified on the host.

The current A and CNAME records have a four-hour TTL, so some resolvers may retain Vercel for up to four hours after the change even if the new records use a 300-second TTL.

## Cutover order

For the requested DNS-first cutover:

1. Apply the three DNS changes.
2. Confirm the authoritative and public answers point to `51.161.153.238`.
3. Redeploy the migration branch to `main` immediately afterward.
4. Verify HTTP redirects, all three TLS certificates, API health, articles, admin authentication, MongoDB health, sitemap URLs, and the favicon.

DNS-first can create a short 404 or certificate gap between a resolver reaching the Sydney host and the new Compose labels being deployed. For a lower-downtime cutover, deploy the new labels before changing DNS, then change DNS and perform a final recreate/verification after propagation.

## Rollback

Before the deployment, DNS rollback is the existing Vercel configuration:

- `@ A 76.76.21.21`
- `www CNAME cname.vercel-dns.com`

The migration keeps the existing MongoDB project, volume, private network, remote app path, and deployment timer identifiers unchanged. A domain rollback therefore does not require moving or restoring data.
