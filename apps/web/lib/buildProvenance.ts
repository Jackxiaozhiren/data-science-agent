"use client";

import * as React from "react";
import { apiUrl } from "@/lib/api";
import { t, type Locale } from "@/lib/locale";

/**
 * Build provenance: which artifact answers, and what would produce the next plan.
 *
 * One module fetches `/version` and one module words the answer, because both facts appear in the
 * persistent status area, in the footer, and on every run page. Three components reading the payload
 * themselves is three vocabularies for `heuristic`, and a diverging label is how a stub deployment ends
 * up described as a model. A value the API did not publish is never rendered: an absent field removes
 * the element rather than substituting a guess.
 */

export type ReasoningMode = {
  mode: string;
  stub: boolean;
  provider: string;
  model: string | null;
  error: string | null;
};

/**
 * Whether this process writes to storage the platform may throw away.
 *
 * `ephemeralRoots` names the roles ("database", "datasets", "artifacts") and never the paths: the API
 * publishes modes because `/version` is unauthenticated. `durable` is the conjunction the UI branches on,
 * and it means only "no root sits on a known throwaway path" -- not a promise about the volume behind it.
 */
export type StorageState = {
  durable: boolean;
  ephemeralRoots: string[];
};

export type BuildProvenance = {
  state: "checking" | "ready" | "unreachable";
  version: string | null;
  distribution: string | null;
  reasoningMode: ReasoningMode | null;
  storage: StorageState | null;
};

const UNKNOWN: BuildProvenance = {
  state: "checking",
  version: null,
  distribution: null,
  reasoningMode: null,
  storage: null,
};

export function useBuildProvenance(): BuildProvenance {
  const [provenance, setProvenance] = React.useState<BuildProvenance>(UNKNOWN);

  React.useEffect(() => {
    let cancelled = false;
    fetch(apiUrl("/version"), { cache: "no-store" })
      .then((res) => (res.ok ? (res.json() as Promise<Record<string, unknown>>) : Promise.reject(new Error(`HTTP ${res.status}`))))
      .then((body) => {
        if (cancelled) return;
        setProvenance({
          state: "ready",
          version: typeof body.version === "string" ? body.version : null,
          distribution: typeof body.distribution === "string" ? body.distribution : null,
          reasoningMode: asReasoningMode(body.reasoning_mode),
          storage: asStorageState(body.storage),
        });
      })
      .catch(() => {
        if (!cancelled) setProvenance({ ...UNKNOWN, state: "unreachable" });
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return provenance;
}

function asStorageState(value: unknown): StorageState | null {
  if (typeof value !== "object" || value === null) return null;
  const record = value as Record<string, unknown>;
  if (typeof record.durable !== "boolean" || !Array.isArray(record.ephemeral_roots)) return null;
  const roots = record.ephemeral_roots.filter((item): item is string => typeof item === "string");
  if (roots.length !== record.ephemeral_roots.length) return null;
  return { durable: record.durable, ephemeralRoots: roots };
}

function asReasoningMode(value: unknown): ReasoningMode | null {
  if (typeof value !== "object" || value === null) return null;
  const record = value as Record<string, unknown>;
  if (typeof record.mode !== "string" || typeof record.stub !== "boolean" || typeof record.provider !== "string") {
    return null;
  }
  return {
    mode: record.mode,
    stub: record.stub,
    provider: record.provider,
    model: typeof record.model === "string" ? record.model : null,
    error: typeof record.error === "string" ? record.error : null,
  };
}

export type ModeDescription = { label: string; short: string; detail: string; modelPlanned: boolean };

export type StorageDescription = { short: string; detail: string };

/**
 * The one wording for the storage disclosure, and the only place that decides it is worth saying.
 *
 * Returns null while the API reports the deployment durable: a warning that fires on nothing is noise that
 * trains readers to ignore the chip. When it does fire, `detail` names which roots are throwaway using the
 * API's own role names, because the alternative -- a generic "data may be lost" -- leaves a reviewer
 * wondering whether the application is broken or the instance is free.
 */
export function describeStorage(state: StorageState, locale: Locale): StorageDescription | null {
  if (state.durable) return null;
  const named =
    state.ephemeralRoots.length > 0 ? state.ephemeralRoots.join(", ") : t(locale, "prov.ephemeralFallback");
  return {
    short: t(locale, "prov.storageNotKept"),
    detail: t(locale, "prov.storageDetail").replace("{roots}", named),
  };
}

/**
 * The one wording for a reasoning mode. `label` and `short` carry the backend's own token (`heuristic`,
 * `real`, `openai`, `ollama`) rather than a coined display term, so a reader can tie what they see to
 * the configuration the operator set; `short` is what the cramped status areas can afford to show.
 *
 * `modelPlanned` is true only when a configured model provider does the planning; the report page
 * states what a run excludes whenever it is false.
 */
export function describeReasoningMode(mode: ReasoningMode, locale: Locale): ModeDescription {
  if (mode.error) {
    return {
      label: t(locale, "prov.modeNotRunnable").replace("{mode}", mode.mode),
      short: t(locale, "prov.modeUnavailableShort").replace("{mode}", mode.mode),
      detail: mode.error,
      modelPlanned: false,
    };
  }
  if (mode.stub) {
    return {
      label: t(locale, "prov.modeLabel").replace("{mode}", mode.mode),
      short: mode.mode,
      detail: t(locale, "prov.heuristicDetail").replace("{mode}", mode.mode),
      modelPlanned: false,
    };
  }
  const plan = `${mode.provider}${mode.model ? ` · ${mode.model}` : ""}`;
  return {
    label: t(locale, "prov.modeLabel").replace("{mode}", plan),
    short: plan,
    detail: t(locale, "prov.modelDetail").replace("{plan}", plan),
    modelPlanned: true,
  };
}
