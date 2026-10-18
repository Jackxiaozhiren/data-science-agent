// R-01: how a screen learns that a dataset is the product's own sample rather than the visitor's upload.
//
// The marker lives in the dataset row's free-form metadata, written by `dsa_api/services/demo_seed.py`, and it
// is the only thing that distinguishes the two. Without one owner for the key and its shape, every page that
// wants to say "sample", offer a starter question, or hide a delete control would re-derive it from a string
// literal -- and §9's naming discipline exists precisely because those copies drift.

import { type Locale } from "@/lib/locale";

export const SAMPLE_MARKER = "dsa_sample_dataset";

type SampleMeta = {
  seeded_by?: string;
  source?: string;
  read_only?: boolean;
  starter_questions?: unknown;
  starter_questions_zh?: unknown;
  verified_by?: unknown;
  example_run_id?: unknown;
};

export type SampleInfo = {
  source: string;
  starterQuestions: string[];
  /** The same questions in the other language the interface offers, position-for-position (R-13). */
  starterQuestionsZh: string[];
  /** The run the sample's report belongs to, so a screen can link straight to a finished report. */
  exampleRunId: string | null;
  readOnly: boolean;
};

function markerOf(metadata: unknown): SampleMeta | null {
  if (typeof metadata !== "object" || metadata === null) return null;
  const marker = (metadata as Record<string, unknown>)[SAMPLE_MARKER];
  if (typeof marker !== "object" || marker === null) return null;
  return marker as SampleMeta;
}

function strings(value: unknown): string[] {
  return Array.isArray(value)
    ? value.filter((item): item is string => typeof item === "string" && item.trim() !== "")
    : [];
}

/** Null for anything the visitor uploaded: an absent marker is not a sample with empty extras. */
export function sampleInfo(metadata: unknown): SampleInfo | null {
  const marker = markerOf(metadata);
  if (!marker) return null;
  const questions = strings(marker.starter_questions);
  const translated = strings(marker.starter_questions_zh);
  return {
    source: typeof marker.source === "string" ? marker.source : "",
    starterQuestions: questions,
    // Shorter than the English list means the payload predates R-13 or the alias table fell back; either way
    // the caller gets `starterQuestions` for that index rather than a list that would mis-pair the two.
    starterQuestionsZh: translated.length === questions.length ? translated : questions,
    exampleRunId: typeof marker.example_run_id === "string" ? marker.example_run_id : null,
    readOnly: marker.read_only === true,
  };
}

/**
 * The questions to offer a visitor who reads `locale`, by index against `starterQuestions`.
 *
 * This is the only place the two lists are chosen between, so a screen cannot offer the Chinese button and
 * send the English sentence -- which would break the promise R-13 makes and the link R-15 counts.
 */
export function starterQuestionsFor(sample: SampleInfo, locale: Locale): string[] {
  return locale === "zh" ? sample.starterQuestionsZh : sample.starterQuestions;
}

export function isSample(metadata: unknown): boolean {
  return sampleInfo(metadata) !== null;
}

/** The first usable starter question for this reader, or null. Ordered by the API's own dataset list. */
export function firstStarter(
  samples: { id: string; sample: SampleInfo }[],
  locale: Locale
): { datasetId: string; question: string } | null {
  for (const entry of samples) {
    const question = starterQuestionsFor(entry.sample, locale)[0];
    if (question) return { datasetId: entry.id, question };
  }
  return null;
}
