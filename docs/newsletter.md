# Newsletter Subscriptions

Status: `1.0`

A small subscribe form sits at the bottom of every page. It collects an email
address, issues a token, and lets the subscriber add their name afterwards with
that token. `/admin` shows how many people have subscribed, along with their
emails and names.

## The Collection

Subscriptions live in MongoDB as `subscribers`.

| Field | Type | Notes |
| --- | --- | --- |
| `email` | string | Lower-cased and trimmed. Unique index. |
| `name` | string | Empty until the subscriber sets it. Max 120 characters. |
| `status` | string | `active` or `unsubscribed`. |
| `tokenHash` | string | HMAC-SHA256 of the token. Unique index. The token itself is never stored. |
| `clientIp` | string | The address the subscription came from, taken from `X-Forwarded-For` / `X-Real-IP` / the socket. |
| `userAgent` | string | Truncated to 300 characters. |
| `source` | string | The page path the subscriber signed up from, e.g. `/articles`. |
| `createdUnix` | float | Seconds since epoch. The canonical creation time. |
| `updatedUnix` | float | Bumped on every change. |
| `unsubscribedUnix` | float \| null | Set once, when they first unsubscribe. |

Timestamps are Unix floats rather than the `createdAt`/`updatedAt` datetimes used
by the older collections. Unix is the canonical representation for new data here;
a raw float is never shown to a person, `/admin` formats it for display.

Unsubscribing keeps the record and flips `status`, so churn stays visible.

## The Token

- Format `jhs_live_<43 url-safe characters>`.
- Only an HMAC-SHA256 hash is stored, with the same server secret and the same
  domain-separated pattern used for admin sessions and the content API key.
- The plaintext is returned exactly once, in the subscribe response.
- It is presented as `Authorization: Bearer <token>` or `X-Subscriber-Token: <token>`.
  It is never accepted from a query string.
- It can set the subscriber's name and unsubscribe them. It can do nothing else,
  and it can never read another subscriber or reach `/api/admin/*`.

Subscribing again with an address that is already on the list rotates the token
and returns it. That is how somebody who has lost their token gets a new one, and
it is why the endpoint needs no separate "resend" route.

## Endpoints

All paths are relative to `https://api.jackhales.com/api`.

| Method | Path | Auth | Purpose |
| --- | --- | --- | --- |
| `POST` | `/subscribers` | none | Subscribe, and receive the token once |
| `GET` | `/subscribers/me` | token | Read your own subscription |
| `PATCH` | `/subscribers/me` | token | Set your name |
| `DELETE` | `/subscribers/me` | token | Unsubscribe |
| `GET` | `/admin/subscribers` | admin session | Count, emails, names, source and IP |

```sh
curl -X POST https://api.jackhales.com/api/subscribers \
  -H 'content-type: application/json' \
  -d '{"email":"reader@example.com","source":"/articles"}'
```

```json
{
  "email": "reader@example.com",
  "name": "",
  "status": "active",
  "createdUnix": 1753776000.12,
  "updatedUnix": 1753776000.12,
  "token": "jhs_live_…"
}
```

```sh
curl -X PATCH https://api.jackhales.com/api/subscribers/me \
  -H 'content-type: application/json' \
  -H 'x-subscriber-token: jhs_live_…' \
  -d '{"name":"A Reader"}'
```

The name is optional, so the subscribe step never blocks on it. The response to a
`PATCH` is the subscription without the token or the IP.

## Guardrails

| Guardrail | Behaviour |
| --- | --- |
| Membership privacy | Subscribing returns the same status code and body shape whether the address is new or already on the list |
| Token failures | Missing, malformed and unknown tokens all return the same `401`, so a token can never confirm that an address exists |
| Field ownership | `createdUnix`, `updatedUnix`, `clientIp`, `status` and `tokenHash` are set by the API; the request model rejects them |
| Unknown fields | Rejected (`extra="forbid"`) rather than silently ignored |
| Volume | At most five *new* subscriptions per IP address per hour, then `429`. An existing subscriber refreshing their token is never blocked |
| Self routes | `/subscribers/me` never returns `clientIp`, `userAgent` or `tokenHash` |
| Admin route | `/api/admin/subscribers` takes the admin session cookie only — never a subscriber token, never the content API key |
| Email shape | Validated once at the boundary; everything downstream trusts it |

The client IP is stored in full rather than hashed, because it exists to be read
in `/admin`. That is a deliberate difference from `articleViews`, which only ever
needs to compare addresses and so stores `ipHash`.

## Admin

`/admin` shows a subscriber tile in the stats row and a panel underneath the
draft API key, listing every subscriber newest first with their email, name,
signup date, source and IP address, plus the total and active counts.
