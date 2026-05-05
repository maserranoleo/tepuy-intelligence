import { apiFetch } from "./client";
import type { GasFieldFeatureCollection } from "@/types/geojson";

export function fetchGasFields(): Promise<GasFieldFeatureCollection> {
  return apiFetch<GasFieldFeatureCollection>("/api/gas_fields");
}
