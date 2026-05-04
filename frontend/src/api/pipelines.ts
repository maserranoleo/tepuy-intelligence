import { apiFetch } from "./client";
import type { PipelineFeatureCollection } from "@/types/geojson";

export function fetchPipelines(): Promise<PipelineFeatureCollection> {
  return apiFetch<PipelineFeatureCollection>("/api/pipelines");
}
