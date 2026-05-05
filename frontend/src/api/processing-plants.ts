import { apiFetch } from "./client";
import type { ProcessingPlantFeatureCollection } from "@/types/geojson";

export function fetchProcessingPlants(): Promise<ProcessingPlantFeatureCollection> {
  return apiFetch<ProcessingPlantFeatureCollection>("/api/processing_plants");
}
