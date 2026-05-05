export type Source = {
  source_name: string;
  source_id?: string | null;
  retrieved_at: string;
  url?: string | null;
  note?: string | null;
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
};

export type PipelineProperties = EntityCommon & {
  length_km?: number | null;
  diameter_in?: number | null;
  capacity_mmcfd?: number | null;
  operator?: string | null;
};

export type GasFieldProperties = EntityCommon & {
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

/** Discriminated union for whatever the user clicked on. */
export type SelectedEntity =
  | { kind: "pipeline"; props: PipelineProperties }
  | { kind: "gas_field"; props: GasFieldProperties };
