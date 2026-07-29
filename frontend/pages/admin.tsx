import { ArrowLeft, Clock3, Copy, FilePenLine, Files, FileText, KeyRound, LogOut, Plus, ShieldAlert, Trash2, Users } from "lucide-react";
import Head from "next/head";
import { useEffect, useState } from "react";

import { ArticleForm, type articlePayload } from "../components/ArticleForm";
import { SiteShell } from "../components/SiteShell";
import { adminFetch } from "../lib/api";
import { formatDate, formatUnixDate } from "../lib/date";
import type { adminStatus, adminSubscriberList, apiKeyIssued, apiKeyMetadata, articleDetail, articleSummary } from "../lib/types";

type adminView = "library" | "new" | "edit";

export default function AdminPage() {
  const [status, setStatus] = useState<adminStatus | null>(null);
  const [email, setEmail] = useState("me@jackhales.com");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [loggedIn, setLoggedIn] = useState(false);
  const [articles, setArticles] = useState<articleSummary[]>([]);
  const [editing, setEditing] = useState<articleDetail | undefined>();
  const [view, setView] = useState<adminView>("library");
  const [message, setMessage] = useState("");
  const [loadingArticle, setLoadingArticle] = useState(false);
  const [submittingCredentials, setSubmittingCredentials] = useState(false);
  const [apiKey, setApiKey] = useState<apiKeyMetadata | null>(null);
  const [apiKeyLabel, setApiKeyLabel] = useState("");
  const [issuedKey, setIssuedKey] = useState("");
  const [apiKeyBusy, setApiKeyBusy] = useState(false);
  const [apiKeyError, setApiKeyError] = useState("");
  const [copied, setCopied] = useState(false);
  const [subscribers, setSubscribers] = useState<adminSubscriberList | null>(null);

  async function loadArticles() {
    const nextArticles = await adminFetch<articleSummary[]>("/admin/articles");
    setArticles(nextArticles);
    setLoggedIn(true);
  }

  async function loadApiKey() {
    try {
      setApiKey(await adminFetch<apiKeyMetadata>("/admin/api-key"));
    } catch {
      // The workspace stays usable when the key service is briefly unavailable.
    }
  }

  async function loadSubscribers() {
    try {
      setSubscribers(await adminFetch<adminSubscriberList>("/admin/subscribers"));
    } catch {
      // The workspace stays usable when the subscribers service is briefly unavailable.
    }
  }

  async function generateApiKey() {
    const replacing = apiKey?.configured;
    if (replacing && !window.confirm("Generating a new key immediately stops the current one from working. Continue?")) return;

    setApiKeyBusy(true);
    setApiKeyError("");
    setCopied(false);
    try {
      const issued = await adminFetch<apiKeyIssued>("/admin/api-key", { method: "POST", body: JSON.stringify({ label: apiKeyLabel.trim() }) });
      const { key, ...metadata } = issued;
      setIssuedKey(key);
      setApiKey(metadata);
      setApiKeyLabel("");
    } catch (error) {
      setApiKeyError(error instanceof Error ? error.message : "Could not generate the API key.");
    } finally {
      setApiKeyBusy(false);
    }
  }

  async function revokeApiKey() {
    if (!window.confirm("Revoke the API key? Any command using it stops working immediately.")) return;

    setApiKeyBusy(true);
    setApiKeyError("");
    try {
      await adminFetch("/admin/api-key", { method: "DELETE" });
      setIssuedKey("");
      await loadApiKey();
    } catch (error) {
      setApiKeyError(error instanceof Error ? error.message : "Could not revoke the API key.");
    } finally {
      setApiKeyBusy(false);
    }
  }

  async function copyIssuedKey() {
    try {
      await navigator.clipboard.writeText(issuedKey);
      setCopied(true);
    } catch {
      setApiKeyError("Copying failed. Select the key and copy it manually.");
    }
  }

  useEffect(() => {
    let active = true;

    async function restoreAdmin() {
      try {
        const nextStatus = await adminFetch<adminStatus>("/admin/status");
        if (!active) return;
        setStatus(nextStatus);
        setEmail(nextStatus.email);

        if (nextStatus.authenticated) {
          try {
            const nextArticles = await adminFetch<articleSummary[]>("/admin/articles");
            if (!active) return;
            setArticles(nextArticles);
            setLoggedIn(true);
            await loadApiKey();
            await loadSubscribers();
          } catch {
            // The session may have expired between the status and article requests.
          }
        }
      } catch (error) {
        if (!active) return;
        setStatus({ configured: true, authenticated: false, email: "me@jackhales.com" });
        setMessage(error instanceof Error ? error.message : "Could not connect to the admin service.");
      }
    }

    restoreAdmin();
    return () => {
      active = false;
    };
  }, []);

  async function submitCredentials() {
    if (!status) return;
    if (!status.configured && password !== confirmPassword) {
      setMessage("Passwords do not match.");
      return;
    }

    setSubmittingCredentials(true);
    setMessage("");
    try {
      const endpoint = status.configured ? "/admin/login" : "/admin/bootstrap";
      await adminFetch(endpoint, { method: "POST", body: JSON.stringify({ email, password }) });
      setPassword("");
      setConfirmPassword("");
      setStatus({ ...status, configured: true, authenticated: true });
      await loadArticles();
      await loadApiKey();
      await loadSubscribers();
      setView("library");
    } finally {
      setSubmittingCredentials(false);
    }
  }

  async function editArticle(slug: string) {
    setLoadingArticle(true);
    setMessage("");
    try {
      const article = await adminFetch<articleDetail>(`/admin/articles/${slug}`);
      setEditing(article);
      setView("edit");
    } finally {
      setLoadingArticle(false);
    }
  }

  function newArticle() {
    setEditing(undefined);
    setMessage("");
    setView("new");
  }

  function showLibrary() {
    setEditing(undefined);
    setMessage("");
    setView("library");
  }

  async function saveArticle(payload: articlePayload) {
    if (view === "edit" && editing) {
      const saved = await adminFetch<articleDetail>(`/admin/articles/${editing.slug}`, { method: "PUT", body: JSON.stringify(payload) });
      setEditing(saved);
      setMessage(saved.status === "published" ? "Published article updated." : "Draft updated.");
    } else {
      const saved = await adminFetch<articleDetail>("/admin/articles", { method: "POST", body: JSON.stringify(payload) });
      setEditing(saved);
      setView("edit");
      setMessage(saved.status === "published" ? "Article published." : "Draft created.");
    }
    await loadArticles();
  }

  async function logout() {
    await adminFetch("/admin/logout", { method: "POST" });
    setLoggedIn(false);
    setArticles([]);
    setEditing(undefined);
    setApiKey(null);
    setIssuedKey("");
    setSubscribers(null);
    setView("library");
    setStatus((current) => current ? { ...current, configured: true, authenticated: false } : current);
  }

  if (!status) {
    return (
      <SiteShell>
        <div className="admin-loading card"><span /> Connecting to the publishing workspace…</div>
      </SiteShell>
    );
  }

  if (!loggedIn) {
    return (
      <SiteShell>
        <Head><title>Admin — Jack Hales</title></Head>
        <div className="admin-login card">
          <span className="icon-tile icon-blue"><FilePenLine size={21} /></span>
          <p className="eyebrow">Publishing workspace</p>
          <h1>{status.configured ? "Welcome back." : "Create your admin account."}</h1>
          <p>{status.configured ? "Sign in to manage articles and drafts." : "First start is reserved for me@jackhales.com. Choose a password with at least 12 characters."}</p>
          <label>
            <span>Email</span>
            <input type="email" autoComplete="username" value={email} readOnly aria-readonly="true" />
          </label>
          <label>
            <span>Password</span>
            <input type="password" autoComplete={status.configured ? "current-password" : "new-password"} value={password} onChange={(event) => setPassword(event.target.value)} onKeyDown={(event) => event.key === "Enter" && status.configured && submitCredentials().catch((error) => setMessage(error.message))} />
          </label>
          {!status.configured ? (
            <label>
              <span>Confirm password</span>
              <input type="password" autoComplete="new-password" value={confirmPassword} onChange={(event) => setConfirmPassword(event.target.value)} onKeyDown={(event) => event.key === "Enter" && submitCredentials().catch((error) => setMessage(error.message))} />
            </label>
          ) : null}
          <button className="button button-dark" disabled={password.length < 12 || (!status.configured && confirmPassword.length < 12) || submittingCredentials} onClick={() => submitCredentials().catch((error) => setMessage(error.message))}>
            {submittingCredentials ? "Please wait…" : status.configured ? "Open workspace" : "Create admin account"}
          </button>
          {message ? <p className="admin-error">{message}</p> : null}
        </div>
      </SiteShell>
    );
  }

  const publishedCount = articles.filter((article) => article.status === "published").length;
  const draftCount = articles.length - publishedCount;

  return (
    <SiteShell>
      <Head><title>Publishing workspace — Jack Hales</title></Head>

      <section className="admin-workspace">
        <header className="admin-heading">
          <div>
            <p className="eyebrow">Publishing workspace</p>
            <h1>{view === "library" ? "Article library" : view === "new" ? "New article" : "Edit article"}</h1>
            <p>{view === "library" ? "Review published work, continue a draft or start something new." : view === "new" ? "Start with a title—the slug will follow automatically." : `Updating ${editing?.title || "article"}.`}</p>
          </div>
          <div className="admin-heading-actions">
            {view === "library" ? (
              <button className="button button-dark" onClick={newArticle}><Plus size={16} /> New article</button>
            ) : (
              <button className="button button-outline" onClick={showLibrary}><ArrowLeft size={16} /> Article library</button>
            )}
            <button className="button button-outline" onClick={logout}><LogOut size={16} /> Logout</button>
          </div>
        </header>

        {view === "library" ? (
          <>
            <div className="admin-stats">
              <div className="admin-stat card"><span className="icon-tile icon-blue"><Files size={19} /></span><div><strong>{articles.length}</strong><small>Total articles</small></div></div>
              <div className="admin-stat card"><span className="icon-tile icon-mint"><FileText size={19} /></span><div><strong>{publishedCount}</strong><small>Published</small></div></div>
              <div className="admin-stat card"><span className="icon-tile icon-peach"><FilePenLine size={19} /></span><div><strong>{draftCount}</strong><small>Drafts</small></div></div>
              <div className="admin-stat card"><span className="icon-tile icon-yellow"><Users size={19} /></span><div><strong>{subscribers?.total ?? 0}</strong><small>Subscribers</small></div></div>
            </div>

            <div className="article-library card">
              <div className="article-library-heading"><div><h2>All articles</h2><p>Newest publication date first</p></div><span>{loadingArticle ? "Opening article…" : `${articles.length} entries`}</span></div>
              <div className="article-library-list">
                {articles.map((article) => (
                  <button key={article.slug} className="admin-article-row" disabled={loadingArticle} onClick={() => editArticle(article.slug).catch((error) => setMessage(error.message))}>
                    <span className={`article-status article-status-${article.status}`}>{article.status}</span>
                    <span className="admin-article-main"><strong>{article.title}</strong><small>{article.summary || "No summary yet."}</small></span>
                    <span className="admin-article-date"><Clock3 size={13} /> {formatDate(article.publishedAt)}</span>
                    <span className="admin-edit-label">Edit <FilePenLine size={14} /></span>
                  </button>
                ))}
                {!articles.length ? <div className="admin-empty"><FileText size={24} /><p>No articles yet.</p><button className="button button-dark" onClick={newArticle}>Create the first article</button></div> : null}
              </div>
            </div>

            <section className="api-key-panel card">
              <div className="api-key-heading">
                <span className="icon-tile icon-blue"><KeyRound size={19} /></span>
                <div>
                  <h2>Draft API key</h2>
                  <p>One key at a time. It can read everything and edit drafts — it can never publish.</p>
                </div>
                <span className={`article-status article-status-${apiKey?.configured ? "published" : "draft"}`}>{apiKey?.configured ? "active" : "none"}</span>
              </div>

              {apiKey?.configured ? (
                <dl className="api-key-facts">
                  <div><dt>Key</dt><dd><code>{apiKey.hint}</code></dd></div>
                  <div><dt>Label</dt><dd>{apiKey.label || "—"}</dd></div>
                  <div><dt>Scope</dt><dd><code>{apiKey.scope}</code></dd></div>
                  <div><dt>Created</dt><dd>{apiKey.createdAt ? formatDate(apiKey.createdAt) : "—"}</dd></div>
                  <div><dt>Last used</dt><dd>{apiKey.lastUsedAt ? formatDate(apiKey.lastUsedAt) : "Never"}</dd></div>
                </dl>
              ) : (
                <p className="api-key-empty">No key is active. Generate one to let a local command work on drafts.</p>
              )}

              {issuedKey ? (
                <div className="api-key-reveal">
                  <p><ShieldAlert size={15} /> Copy this now — it is shown once and never again.</p>
                  <code>{issuedKey}</code>
                  <button className="button button-outline" onClick={() => copyIssuedKey()}><Copy size={15} /> {copied ? "Copied" : "Copy key"}</button>
                </div>
              ) : null}

              <div className="api-key-actions">
                <label>
                  <span>Label</span>
                  <input value={apiKeyLabel} maxLength={80} placeholder="plumb adapter" onChange={(event) => setApiKeyLabel(event.target.value)} />
                </label>
                <button className="button button-dark" disabled={apiKeyBusy} onClick={() => generateApiKey()}>
                  <KeyRound size={16} /> {apiKeyBusy ? "Working…" : apiKey?.configured ? "Generate new key" : "Generate API key"}
                </button>
                {apiKey?.configured ? (
                  <button className="button button-outline" disabled={apiKeyBusy} onClick={() => revokeApiKey()}><Trash2 size={16} /> Revoke</button>
                ) : null}
              </div>

              {apiKeyError ? <p className="admin-error">{apiKeyError}</p> : null}
            </section>

            <section className="subscribers-panel card">
              <div className="subscribers-heading">
                <span className="icon-tile icon-yellow"><Users size={19} /></span>
                <div>
                  <h2>Subscribers</h2>
                  <p>{subscribers ? `${subscribers.active} active of ${subscribers.total} total.` : "Newest sign-ups first."}</p>
                </div>
              </div>

              {subscribers?.subscribers.length ? (
                <div className="subscribers-list-wrap">
                  <table className="subscribers-table">
                    <thead>
                      <tr>
                        <th scope="col">Email</th>
                        <th scope="col">Name</th>
                        <th scope="col">Signed up</th>
                        <th scope="col">Source</th>
                        <th scope="col">IP</th>
                      </tr>
                    </thead>
                    <tbody>
                      {subscribers.subscribers.map((sub) => (
                        <tr key={sub.id} className={sub.status === "active" ? undefined : "subscriber-inactive"}>
                          <td>
                            <span className="subscriber-email">{sub.email}</span>
                            {sub.status === "active" ? null : <span className="subscriber-status-tag">unsubscribed</span>}
                          </td>
                          <td>{sub.name ? sub.name : <span className="subscriber-name-empty">—</span>}</td>
                          <td className="subscribers-meta-cell">{formatUnixDate(sub.createdUnix)}</td>
                          <td className="subscribers-meta-cell">{sub.source || "—"}</td>
                          <td className="subscribers-meta-cell">{sub.clientIp}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <div className="admin-empty"><Users size={24} /><p>No subscribers yet.</p></div>
              )}
            </section>

            {message ? <div className="admin-toast">{message}</div> : null}
          </>
        ) : (
          <div className="article-editor-shell card">
            {message ? <div className="admin-success">{message}</div> : null}
            <ArticleForm key={editing?.id || "new"} article={editing} mode={view === "new" ? "create" : "edit"} onSubmit={saveArticle} onCancel={showLibrary} />
          </div>
        )}
      </section>
    </SiteShell>
  );
}
