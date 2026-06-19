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
