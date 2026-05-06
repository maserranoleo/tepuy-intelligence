export type Source = {
  source_name: string;
  source_id?: string | null;
  retrieved_at: string;
  url?: string | null;
  note?: string | null;
};

export type SanctionsMatch = {
  ent_num: number;
  matched_name: string;
  sdn_type?: string | null;
  programs: string[];
  matched_tokens: string[];
  venezuela_program: boolean;
  ofac_url: string;
};

/** Shared properties present on every entity, regardless of geometry type. */
export type EntityCommon = {
  id: string;
  name: string;
  name_es?: string | null;
  aliases: string[];
  status: string;
  status_as_of?: string | null;
  properties: Record<string, unknown>;
  external_ids: Record<string, string>;
  sources: Source[];
  /** Potential OFAC SDN matches against this entity's operator string.
   *  Empty when the SDN list hasn't been ingested or the operator is null. */
  sanctions: SanctionsMatch[];
};

export type PipelineProperties = EntityCommon & {
  length_km?: number | null;
  diameter_in?: number | null;
  capacity_mmcfd?: number | null;
  operator?: string | null;
};

/** FIRMS proximity classifier output (5 km / 30 days). All zero/null when
 *  no FIRMS data has been ingested. */
export type FlareProximity = {
  recent_flare_count: number;
  last_flare_at?: string | null;
  peak_frp_mw?: number | null;
};

export type GasFieldProperties = EntityCommon &
  FlareProximity & {
    operator?: string | null;
  };

export type ProcessingPlantProperties = EntityCommon &
  FlareProximity & {
    operator?: string | null;
  };

export type PipelineFeature = {
  type: "Feature";
  geometry:
    | { type: "LineString"; coordinates: [number, number][] }
    | { type: "MultiLineString"; coordinates: [number, number][][] };
  properties: PipelineProperties;
};

export type PipelineFeatureCollection = {
  type: "FeatureCollection";
  features: PipelineFeature[];
};

export type GasFieldFeature = {
  type: "Feature";
  geometry: { type: "Point"; coordinates: [number, number] };
  properties: GasFieldProperties;
};

export type GasFieldFeatureCollection = {
  type: "FeatureCollection";
  features: GasFieldFeature[];
};

export type ProcessingPlantFeature = {
  type: "Feature";
  geometry: { type: "Point"; coordinates: [number, number] };
  properties: ProcessingPlantProperties;
};

export type ProcessingPlantFeatureCollection = {
  type: "FeatureCollection";
  features: ProcessingPlantFeature[];
};

export type FlareEventProperties = {
  id: string;
  acquired_at: string;
  satellite?: string | null;
  instrument?: string | null;
  confidence?: string | null;
  daynight?: string | null;
  brightness_ti4?: number | null;
  brightness_ti5?: number | null;
  frp?: number | null;
  source_name: string;
  external_id: string;
  sources: Source[];
};

export type FlareEventFeature = {
  type: "Feature";
  geometry: { type: "Point"; coordinates: [number, number] };
  properties: FlareEventProperties;
};

export type FlareEventFeatureCollection = {
  type: "FeatureCollection";
  features: FlareEventFeature[];
};

/** Discriminated union for whatever the user clicked on. */
export type SelectedEntity =
  | { kind: "pipeline"; props: PipelineProperties }
  | { kind: "gas_field"; props: GasFieldProperties }
  | { kind: "processing_plant"; props: ProcessingPlantProperties }
  | { kind: "flare_event"; props: FlareEventProperties };
