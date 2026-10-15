// R-01: how a screen learns that a dataset is the product's own sample rather than the visitor's upload.
//
// The marker lives in the dataset row's free-form metadata, written by `dsa_api/services/demo_seed.py`, and it
// is the only thing that distinguishes the two. Without one owner for the key and its shape, every page that
// wants to say "sample", offer a starter question, or hide a delete control would re-derive it from a string
// literal -- and §9's naming discipline exists precisely because those copies drift.

export const SAMPLE_MARKER = "dsa_sample_dataset";

type SampleMeta = {
  seeded_by?: string;
  source?: string;
  read_only?: boolean;
  starter_questions?: unknown;
  verified_by?: unknown;
  example_run_id?: unknown;
};

export type SampleInfo = {
  source: string;
  starterQuestions: string[];
  /** The dataset the run belongs to, so a screen can link straight to a finished report. */
  exampleRunId: string | null;
  readOnly: boolean;
};

function markerOf(metadata: unknown): SampleMeta | null {
  if (typeof metadata !== "object" || metadata === null) return null;
  const marker = (metadata as Record<string, unknown>)[SAMPLE_MARKER];
  if (typeof marker !== "object" || marker === null) return null;
  return marker as SampleMeta;
}

/** Null for anything the visitor uploaded: an absent marker is not a sample with empty extras. */
export function sampleInfo(metadata: unknown): SampleInfo | null {
  const marker = markerOf(metadata);
  if (!marker) return null;
  const questions = Array.isArray(marker.starter_questions)
    ? marker.starter_questions.filter((item): item is string => typeof item === "string" && item.trim() !== "")
    : [];
  return {
    source: typeof marker.source === "string" ? marker.source : "",
    starterQuestions: questions,
    exampleRunId: typeof marker.example_run_id === "string" ? marker.example_run_id : null,
    readOnly: marker.read_only === true,
  };
}

export function isSample(metadata: unknown): boolean {
  return sampleInfo(metadata) !== null;
}

/** The first usable starter question, or null. Ordered by the API's own dataset list, which is newest first. */
export function firstStarter(samples: { id: string; sample: SampleInfo }[]): { datasetId: string; question: string } | null {
  for (const entry of samples) {
    const question = entry.sample.starterQuestions[0];
    if (question) return { datasetId: entry.id, question };
  }
  return null;
}
