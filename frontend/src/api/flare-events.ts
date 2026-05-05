import { apiFetch } from "./client";
import type { FlareEventFeatureCollection } from "@/types/geojson";

export function fetchFlareEvents(days = 14): Promise<FlareEventFeatureCollection> {
  return apiFetch<FlareEventFeatureCollection>(`/api/flare_events?days=${days}`);
}
