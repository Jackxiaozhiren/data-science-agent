"use client";

// R-05: the model credential, set inside the product and kept on this machine.
//
// Two rules shape this page, and both are visible in the code. The credential field is write-only: the API
// never returns the value, so nothing here can display it, and an empty field means "keep what is stored"
// rather than "clear it" -- clearing is the explicit checkbox. And when the instance refuses to accept a key at
// all, the page says why and names the command that does accept one, instead of showing a form that would fail.
import { useEffect, useState } from "react";
import { Loader2, KeyRound, Trash2 } from "lucide-react";
import { clientFetch, classifyResponse, FAILURE_PRESENTATION, type ApiFailure } from "@/lib/api";
import { Button } from "@/app/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/app/components/ui/card";
import { Input, Select } from "@/app/components/ui/input";
import { PageHeader } from "@/app/components/data/PageHeader";
import { ErrorState } from "@/app/components/data/States";

type Effective = { mode: string; provider: string; model: string | null; source: string; error: string | null };

type View = {
  local_settings: boolean;
  accepts_remote_writes: boolean;
  stored: Record<string, string | boolean>;
  stored_problem: string | null;
  settings_file_readable_by_others: boolean;
  effective: Effective;
  providers: string[];
  suggestion: string;
};

const MODES = [
  { value: "heuristic", label: "Local planner — no model, no cost, no data leaves this machine" },
  { value: "real", label: "Real model — sends your question and your data to the endpoint below" },
];

export default function SettingsPage() {
  const [view, setView] = useState<View | null>(null);
  const [failure, setFailure] = useState<ApiFailure | null>(null);
  const [mode, setMode] = useState("heuristic");
  const [provider, setProvider] = useState("ollama");
  const [model, setModel] = useState("");
  const [baseUrl, setBaseUrl] = useState("");
  const [credential, setCredential] = useState("");
  const [clearCredential, setClearCredential] = useState(false);
  const [saving, setSaving] = useState<"idle" | "sending" | "saved">("idle");
  const [notice, setNotice] = useState<string | null>(null);

  async function refresh() {
    try {
      const res = await clientFetch("/api/v1/provider");
      const kind = classifyResponse(res);
      if (kind) {
        setFailure(kind);
        return;
      }
      const loaded = (await res.json()) as View;
      setView(loaded);
      setFailure(null);
      setMode(loaded.effective.mode);
      setProvider(String(loaded.stored?.provider ?? loaded.providers[0] ?? "ollama"));
      setModel(String(loaded.stored?.model ?? ""));
      setBaseUrl(String(loaded.stored?.base_url ?? ""));
    } catch {
      setFailure("transport");
    }
  }

  useEffect(() => {
    void refresh();
  }, []);

  async function save() {
    setSaving("sending");
    setNotice(null);
    const body: Record<string, string> = { mode, provider };
    if (model.trim()) body.model = model.trim();
    if (baseUrl.trim()) body.base_url = baseUrl.trim();
    // Only send a credential when one was typed, or when the visitor asked for the stored one to be removed.
    // Anything else would overwrite it, and the page cannot read it back to resend it.
    if (credential) body.api_key = credential;
    else if (clearCredential) body.api_key = "";
    try {
      const res = await clientFetch("/api/v1/provider", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      const kind = classifyResponse(res);
      if (kind) {
        setNotice(res.status === 403 ? (await res.json()).detail : FAILURE_PRESENTATION[kind]);
        setSaving("idle");
        return;
      }
      const saved = (await res.json()) as { note: string; effective: Effective };
      setNotice(saved.note);
      setCredential("");
      setSaving("saved");
      await refresh();
    } catch {
      setNotice(FAILURE_PRESENTATION.transport);
      setSaving("idle");
    }
  }

  async function forget() {
    setNotice(null);
    try {
      const res = await clientFetch("/api/v1/provider", { method: "DELETE" });
      if (classifyResponse(res)) {
        setNotice(`The settings could not be cleared: ${res.status}.`);
        return;
      }
      setNotice("Stored settings deleted. The key stays only if your shell exported one.");
      await refresh();
    } catch {
      setNotice(FAILURE_PRESENTATION.transport);
    }
  }

  if (failure) {
    return (
      <div className="mx-auto max-w-3xl px-6 py-10">
        <PageHeader eyebrow="This instance" title="Model settings" description="Choose what produces the plan." />
        <ErrorState message={FAILURE_PRESENTATION[failure]} />
      </div>
    );
  }

  if (!view) {
    return (
      <div className="mx-auto max-w-3xl px-6 py-10">
        <PageHeader eyebrow="This instance" title="Model settings" description="Choose what produces the plan." />
        <p className="flex items-center gap-2 text-sm text-zinc-500">
          <Loader2 className="size-4 animate-spin" aria-hidden /> Loading this instance&apos;s settings
        </p>
      </div>
    );
  }

  if (!view.local_settings) {
    return (
      <div className="mx-auto max-w-3xl px-6 py-10">
        <PageHeader eyebrow="This instance" title="Model settings" description="Why this deployment has no key field." />
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">This instance does not accept a model credential</CardTitle>
            <CardDescription className="text-xs">
              A hosted demo has nowhere to keep a secret between visits, and a key that is accepted and then
              lost on restart is worse than one that is refused. So the setting is not partially supported
              here: it is off, and the reason is on the page.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3 text-sm">
            <p>
              Run the product on your own machine instead. <code className="rounded bg-zinc-100 px-1">dsa ui</code>{" "}
              keeps its settings in the data directory you chose, reads them from disk on every run, and sends
              nothing anywhere you did not point it at.
            </p>
            <p className="text-xs text-zinc-500">
              Right now this process resolves its plans with: mode <strong>{view.effective.mode}</strong>,
              provider <strong>{view.effective.provider}</strong>, decided by{" "}
              <strong>{view.effective.source}</strong>.
            </p>
          </CardContent>
        </Card>
      </div>
    );
  }

  const hasCredential = view.stored.has_credential === true;

  return (
    <div className="mx-auto max-w-3xl px-6 py-10">
      <PageHeader
        eyebrow="This instance"
        title="Model settings"
        description="What produces the plan, and where the credential lives."
      />
      <div className="space-y-6">
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Currently in effect</CardTitle>
            <CardDescription className="text-xs">
              Read from the process that will run your next analysis, not from a label.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-2 text-sm">
            <p>
              mode <strong>{view.effective.mode}</strong> · provider{" "}
              <strong>{view.effective.provider}</strong> · model{" "}
              <strong>{view.effective.model ?? "—"}</strong> · decided by{" "}
              <strong>{view.effective.source}</strong>
            </p>
            {view.effective.error && (
              <p className="text-xs text-amber-800" role="status">
                {view.effective.error}
              </p>
            )}
            {view.stored_problem && (
              <p className="text-xs text-red-700" role="status">
                {view.stored_problem}
              </p>
            )}
            {view.settings_file_readable_by_others && (
              <p className="text-xs text-red-700" role="alert">
                The settings file is readable by other users on this machine. Re-save the settings to restore
                0600, or check the directory&apos;s permissions.
              </p>
            )}
            <p className="text-xs text-zinc-500">{view.suggestion}</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-sm flex items-center gap-2">
              <KeyRound className="size-4" aria-hidden /> Configure a provider
            </CardTitle>
            <CardDescription className="text-xs">
              Saved to a file in this instance&apos;s data directory, readable only by your user. The value is
              never sent back to this page, so the field above stays empty after a save — that is deliberate,
              not a bug.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <label className="block text-sm">
              <span className="mb-1 block text-xs font-medium text-zinc-600">Mode</span>
              <Select value={mode} onChange={(e) => setMode(e.target.value)}>
                {MODES.map((m) => (
                  <option key={m.value} value={m.value}>
                    {m.label}
                  </option>
                ))}
              </Select>
            </label>

            <label className="block text-sm">
              <span className="mb-1 block text-xs font-medium text-zinc-600">Provider</span>
              <Select value={provider} onChange={(e) => setProvider(e.target.value)}>
                {view.providers.map((name) => (
                  <option key={name} value={name}>
                    {name}
                  </option>
                ))}
              </Select>
            </label>

            <label className="block text-sm">
              <span className="mb-1 block text-xs font-medium text-zinc-600">Model name</span>
              <Input
                value={model}
                onChange={(e) => setModel(e.target.value)}
                placeholder={provider === "ollama" ? "qwen3:8b" : "as the endpoint names it"}
              />
            </label>

            <label className="block text-sm">
              <span className="mb-1 block text-xs font-medium text-zinc-600">Endpoint</span>
              <Input
                value={baseUrl}
                onChange={(e) => setBaseUrl(e.target.value)}
                placeholder={
                  provider === "ollama" ? "http://localhost:11434/v1" : "https://… /v1 (OpenAI-compatible)"
                }
              />
            </label>

            <label className="block text-sm">
              <span className="mb-1 block text-xs font-medium text-zinc-600">
                Credential {hasCredential ? "(one is already stored)" : ""}
              </span>
              <Input
                type="password"
                value={credential}
                onChange={(e) => setCredential(e.target.value)}
                autoComplete="off"
                spellCheck={false}
                placeholder={hasCredential ? "leave blank to keep the stored one" : "paste the key for this endpoint"}
              />
              <span className="mt-1 flex items-center gap-2 text-xs text-zinc-500">
                <input
                  type="checkbox"
                  id="clear-credential"
                  checked={clearCredential}
                  onChange={(e) => setClearCredential(e.target.checked)}
                />
                <label htmlFor="clear-credential">Remove the stored credential</label>
              </span>
            </label>

            <div className="flex flex-wrap items-center gap-3">
              <Button onClick={() => void save()} disabled={saving === "sending"}>
                {saving === "sending" ? "Saving" : "Save settings"}
              </Button>
              <Button variant="secondary" onClick={() => void forget()}>
                <Trash2 className="size-4" aria-hidden /> Delete settings file
              </Button>
              {saving === "saved" && <span className="text-xs text-emerald-700">Saved.</span>}
            </div>

            {notice && (
              <p className="text-xs text-zinc-600" role="status">
                {notice}
              </p>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
