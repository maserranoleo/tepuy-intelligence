export type Source = {
  source_name: string;
  source_id?: string | null;
  retrieved_at: string;
  url?: string | null;
  note?: string | null;
};

export type PipelineProperties = {
  id: string;
  name: string;
  name_es?: string | null;
  aliases: string[];
  status: string;
  status_as_of?: string | null;
  length_km?: number | null;
  diameter_in?: number | null;
  capacity_mmcfd?: number | null;
  operator?: string | null;
  properties: Record<string, unknown>;
  external_ids: Record<string, string>;
  sources: Source[];
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
