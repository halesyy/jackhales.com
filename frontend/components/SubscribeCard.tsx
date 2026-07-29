import { CircleCheck, Send } from "lucide-react";
import { useEffect, useState, type FormEvent } from "react";

import { apiError, fetchSubscriber, subscribeToUpdates, unsubscribe, updateSubscriberName } from "../lib/api";

const subscriberTokenKey = "jackhales.subscriberToken";

type cardPhase = "checking" | "idle" | "submitting" | "subscribed";

function readStoredToken(): string | null {
  try {
    return window.localStorage.getItem(subscriberTokenKey);
  } catch {
    return null;
  }
}

function writeStoredToken(token: string) {
  try {
    window.localStorage.setItem(subscriberTokenKey, token);
  } catch {
    // A visitor with storage disabled can still subscribe — we just won't recognise them next visit.
  }
}

function clearStoredToken() {
  try {
    window.localStorage.removeItem(subscriberTokenKey);
  } catch {
    // Nothing to clean up if storage was never reachable.
  }
}

function describeError(error: unknown): string {
  if (error instanceof apiError) {
    if (error.status === 429) return "That's a few too many sign-ups from here — try again a bit later.";
    if (error.status === 422) return "That doesn't look like a valid email address — mind checking it?";
  }
  return "Something went wrong on our end — please try again in a moment.";
}

export function SubscribeCard() {
  const [phase, setPhase] = useState<cardPhase>("checking");
  const [email, setEmail] = useState("");
  const [name, setName] = useState("");
  const [token, setToken] = useState<string | null>(null);
  const [nameSaving, setNameSaving] = useState(false);
  const [nameSaved, setNameSaved] = useState(false);
  const [leaving, setLeaving] = useState(false);
  const [error, setError] = useState("");

  // Runs once on mount (client-only) so a returning visitor with a stored token skips straight
  // to the subscribed state instead of flashing the idle form first.
  useEffect(() => {
    let active = true;
    const stored = readStoredToken();

    if (!stored) {
      setPhase("idle");
      return;
    }

    fetchSubscriber(stored)
      .then((data) => {
        if (!active) return;
        if (data.status === "active") {
          setToken(stored);
          setName(data.name || "");
          setPhase("subscribed");
        } else {
          // The token is valid but no longer marks an active subscriber — treat it like a fresh visitor.
          clearStoredToken();
          setPhase("idle");
        }
      })
      .catch((err) => {
        if (!active) return;
        if (err instanceof apiError && err.status === 401) clearStoredToken();
        setPhase("idle");
      });

    return () => {
      active = false;
    };
  }, []);

  async function handleSubscribe(event: FormEvent) {
    event.preventDefault();
    if (phase === "submitting" || !email.trim()) return;

    setError("");
    setPhase("submitting");
    try {
      const issued = await subscribeToUpdates({ email: email.trim(), source: window.location.pathname });
      writeStoredToken(issued.token);
      setToken(issued.token);
      setName(issued.name || "");
      setPhase("subscribed");
    } catch (err) {
      setPhase("idle");
      setError(describeError(err));
    }
  }

  async function handleSaveName(event: FormEvent) {
    event.preventDefault();
    if (!token || nameSaving || !name.trim()) return;

    setNameSaving(true);
    setError("");
    try {
      const updated = await updateSubscriberName(token, name.trim());
      setName(updated.name || "");
      setNameSaved(true);
    } catch (err) {
      setError(describeError(err));
    } finally {
      setNameSaving(false);
    }
  }

  // The card promises "unsubscribe any time", so it has to offer it rather than leave that to an email footer.
  async function handleUnsubscribe() {
    if (!token || leaving) return;

    setLeaving(true);
    setError("");
    try {
      await unsubscribe(token);
      clearStoredToken();
      setToken(null);
      setName("");
      setEmail("");
      setNameSaved(false);
      setPhase("idle");
    } catch (err) {
      setError(describeError(err));
    } finally {
      setLeaving(false);
    }
  }

  return (
    <section className="subscribe-card card" aria-labelledby="subscribe-heading">
      <div className="subscribe-copy">
        <p className="eyebrow">Stay in the loop</p>
        <h2 id="subscribe-heading">Get a note when something new goes up.</h2>
        <p className="subscribe-lead">Short, occasional updates — no spam, unsubscribe any time.</p>
      </div>

      <div className="subscribe-body" role="status" aria-live="polite">
        {phase === "checking" ? (
          <div className="subscribe-row">
            <div className="subscribe-skeleton" aria-hidden="true" />
            <span className="sr-only">Checking your subscription status…</span>
          </div>
        ) : phase === "subscribed" ? (
          <div className="subscribe-confirmed">
            <p className="subscribe-confirmed-line">
              <CircleCheck size={16} /> You&apos;re on the list.
            </p>
            <form className="subscribe-row" onSubmit={handleSaveName}>
              <div className="subscribe-field">
                <label htmlFor="subscribe-name" className="sr-only">Your name (optional)</label>
                <input
                  id="subscribe-name"
                  type="text"
                  autoComplete="name"
                  maxLength={120}
                  placeholder="Add your name (optional)"
                  value={name}
                  disabled={nameSaving}
                  onChange={(event) => {
                    setName(event.target.value);
                    setNameSaved(false);
                  }}
                />
              </div>
              <button type="submit" className="button button-outline" disabled={nameSaving || !name.trim()}>
                {nameSaving ? "Saving…" : "Save name"}
              </button>
            </form>
            <p className={nameSaved ? "subscribe-note" : "subscribe-note subscribe-note-muted"}>
              {nameSaved ? "Saved — thanks." : "Optional — only so a hello can use it."}
              <button type="button" className="subscribe-leave" disabled={leaving} onClick={() => handleUnsubscribe()}>
                {leaving ? "Removing…" : "Unsubscribe"}
              </button>
            </p>
          </div>
        ) : (
          <form className="subscribe-row" onSubmit={handleSubscribe}>
            <div className="subscribe-field">
              <label htmlFor="subscribe-email" className="sr-only">Email address</label>
              <input
                id="subscribe-email"
                type="email"
                autoComplete="email"
                inputMode="email"
                required
                placeholder="you@email.com"
                value={email}
                disabled={phase === "submitting"}
                onChange={(event) => setEmail(event.target.value)}
              />
            </div>
            <button type="submit" className="button button-dark" disabled={phase === "submitting" || !email.trim()}>
              <Send size={16} /> {phase === "submitting" ? "Subscribing…" : "Subscribe"}
            </button>
          </form>
        )}
        {error ? <p className="subscribe-error">{error}</p> : null}
      </div>
    </section>
  );
}
