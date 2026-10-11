"use client";

import * as React from "react";
import { apiUrl } from "@/lib/api";

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

export type BuildProvenance = {
  state: "checking" | "ready" | "unreachable";
  version: string | null;
  distribution: string | null;
  reasoningMode: ReasoningMode | null;
};

const UNKNOWN: BuildProvenance = {
  state: "checking",
  version: null,
  distribution: null,
  reasoningMode: null,
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

/**
 * The one wording for a reasoning mode. `label` and `short` carry the backend's own token (`heuristic`,
 * `real`, `openai`, `ollama`) rather than a coined display term, so a reader can tie what they see to
 * the configuration the operator set; `short` is what the cramped status areas can afford to show.
 *
 * `modelPlanned` is true only when a configured model provider does the planning; the report page
 * states what a run excludes whenever it is false.
 */
export function describeReasoningMode(mode: ReasoningMode): ModeDescription {
  if (mode.error) {
    return {
      label: `Reasoning mode: ${mode.mode} — not runnable`,
      short: `${mode.mode} (unavailable)`,
      detail: mode.error,
      modelPlanned: false,
    };
  }
  if (mode.stub) {
    return {
      label: `Reasoning mode: ${mode.mode}`,
      short: mode.mode,
      detail:
        `This API instance plans with deterministic rules (DSA_LLM_MODE=${mode.mode}): no language ` +
        "model is called when a run starts here, so nothing about a question is interpreted beyond " +
        "keyword matching. The tool calls, evidence, statistics and validation in a report are " +
        "computed from the data either way.",
      modelPlanned: false,
    };
  }
  return {
    label: `Reasoning mode: ${mode.provider}${mode.model ? ` · ${mode.model}` : ""}`,
    short: `${mode.provider}${mode.model ? ` · ${mode.model}` : ""}`,
    detail: `This API instance plans with ${mode.provider}${mode.model ? ` (${mode.model})` : ""}; evidence and validation are computed from the data.`,
    modelPlanned: true,
  };
}
