// Mirror of the backend Pydantic DTOs (api/naturascreen/schemas.py). Kept narrow to the
// fields the UI consumes.

export interface Compound {
  id: number;
  name: string;
  smiles: string;
  inchikey: string | null;
  source_organism: string | null;
  source_db: string;
  coconut_id: string | null;
  molecular_descriptors: Record<string, number | number[]>;
  references: unknown[];
  created_at: string;
}

export interface CompoundPage {
  items: Compound[];
  total: number;
  limit: number;
  offset: number;
}

export interface AdapterStatus {
  available: boolean;
  tool: string;
}

export interface Meta {
  version: string;
  disclaimer: string;
  simulation_notice: string;
  adapters: {
    docking: AdapterStatus;
    neoantigen: AdapterStatus;
    response: AdapterStatus;
  };
}

// --- Live simulation stream (mirror of the websocket payloads) ---

export interface SimMeta {
  type: "meta";
  disclaimer: string;
  illustrative_notice: string;
  effectiveness: number;
  seed: number;
  steps: number;
  source: string;
  transfer: {
    k_division_suppression: number;
    k_death_induction: number;
    formula: string;
    note: string;
  };
}

export interface SimFrame {
  type: "frame";
  illustrative_notice: string;
  t: number;
  time: number;
  positions: number[]; // flat xyz
  states: number[]; // 0 dividing, 1 stressed, 2 dying
  population: number;
  baseline_population: number;
  counts: { dividing?: number; stressed?: number; dying?: number };
}

export interface SimEnd {
  type: "end";
  illustrative_notice: string;
  final_population: number;
  baseline_population: number;
  reduction_pct: number;
}

export type StreamStatus = "idle" | "connecting" | "streaming" | "done" | "error";

// --- Experiments / targets ---

export interface TargetOut {
  id: number;
  type: string;
  pdb_id: string | null;
  gene: string | null;
  description: string | null;
  dockable: boolean;
  box_source: string | null;
}

export interface ExperimentSummary {
  id: number;
  status: string;
  target_id: number | null;
  compound_set: number[];
  weights: Record<string, number>;
  error: string | null;
  created_at: string;
}

export interface ScoredCompound {
  compound_id: number;
  name: string;
  coconut_id: string | null;
  smiles: string;
  rank: number;
  combined_score: number;
  normalized: Record<string, number | null>;
  breakdown: Record<string, unknown>;
  warnings: string[];
}

export interface ExperimentResults {
  disclaimer: string;
  illustrative_notice: string;
  experiment: ExperimentSummary;
  ranked: ScoredCompound[];
  simulation: {
    compound_id: number;
    baseline_population: number;
    final_population: number;
    reduction_pct: number;
  } | null;
}
