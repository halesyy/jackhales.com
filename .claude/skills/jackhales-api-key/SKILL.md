---
name: jackhales-api-key
description: Set up, verify, or rotate the single jackhales.com content API key for a local command or the Plumb adapter. Use when the content command reports a missing key, when the key needs rotating, or when wiring a new machine or agent to the draft content API.
---

# Jack Hales API Key

One key exists at a time. Generating a new one in `/admin` immediately stops the
old one from working.

## Never Handle The Value

- Do not print the key, echo it, or place it in a command argument, file, commit,
  plan, log, or prompt.
- Do not paste a key the user typed into chat back into a command line. Route it
  through the hidden Keychain prompt instead.
- Only the last six characters are ever displayed, as part of the stored hint.

## Check What Already Exists

```sh
JACKHALES_ROOT="${JACKHALES_ROOT:-$HOME/dev/jackhales.com}"
"$JACKHALES_ROOT/scripts/jackhales-content" status
```

`status` reports the base URL, the resolution order, and whether a key is
available — never the key itself. Resolution order is `JACKHALES_API_KEY` first,
then the macOS Keychain at `keychain:macos:com.jackhales.api/content`.

If it reports `ready`, confirm it against the live API before doing anything else:

```sh
"$JACKHALES_ROOT/scripts/jackhales-content" whoami
```

A `401` means the key was superseded or revoked in `/admin` and a new one is needed.

## Generate A Key

Ask Jack to do this himself — key generation is behind the admin session and is
not something to automate:

1. Open `https://jackhales.com/admin` and sign in.
2. In **Draft API key**, optionally set a label such as `plumb adapter`.
3. Choose **Generate API key**. The key is shown once.

Warn before rotating: any command or agent using the previous key stops working.

## Store It

Locally, through the hidden Keychain prompt in an interactive terminal:

```sh
"$JACKHALES_ROOT/scripts/jackhales-content" login
"$JACKHALES_ROOT/scripts/jackhales-content" login --apply
```

Review the plan first. The apply path hands the prompt to macOS Keychain, so the
value never passes through the shell.

For Plumb, use the adapter's own credential command instead so the key lands in
Plumb's credential store:

```sh
"${PLUMB_ROOT:-$HOME/dev/plumb}/scripts/plumb" services jackhales access status
"${PLUMB_ROOT:-$HOME/dev/plumb}/scripts/plumb" services jackhales access connect --apply
```

In a deployed runtime, set `JACKHALES_API_KEY` in that runtime's secret store.
Never add it to `.env.example`, `docker-compose.yml`, or any tracked file.

## Verify

```sh
"$JACKHALES_ROOT/scripts/jackhales-content" status
"$JACKHALES_ROOT/scripts/jackhales-content" whoami
"$JACKHALES_ROOT/scripts/jackhales-content" list --status draft
```

`whoami` should report scope `articles:draft` and `canPublish: false`. Report the
resolved secret reference, the scope, and the read-only check. Never the key.

## Revoke

Revoking is done in `/admin` with **Revoke**. There is no API-key route that can
revoke or reissue a key — that would let a compromised key extend itself.
