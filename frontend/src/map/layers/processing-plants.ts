import type { Map as MLMap } from "maplibre-gl";
import type { FeatureCollection } from "geojson";
import { fetchProcessingPlants } from "@/api/processing-plants";
import type { LayerConfig, LayerContext } from "../LayerRegistry";
import type { ProcessingPlantProperties } from "@/types/geojson";

const SRC_ID = "processing-plants-src";
const CIRCLE_ID = "processing-plants-circle";

// Cyan/blue palette to differentiate from green-family gas fields.
// Color encodes status (consistent with every other entity); plant_type
// lives in properties for filtering when we add a UI for it.
const STATUS_COLOR: Record<string, string> = {
  operating: "#22d3ee",   // cyan-400
  construction: "#0ea5e9", // sky-500
  proposed: "#94a3b8",    // slate-400
  idle: "#64748b",        // slate-500
  retired: "#475569",     // slate-600
  unknown: "#6b7280",     // gray-500
};

const COLOR_EXPR = [
  "match",
  ["get", "status"],
  "operating", STATUS_COLOR.operating,
  "construction", STATUS_COLOR.construction,
  "proposed", STATUS_COLOR.proposed,
  "idle", STATUS_COLOR.idle,
  "retired", STATUS_COLOR.retired,
  STATUS_COLOR.unknown,
] as unknown as never;

export const processingPlantsLayer: LayerConfig = {
  id: "processing_plants",
  label: "Processing & Compression Plants",
  layerIds: [CIRCLE_ID],
  searchable: true,
  fetch: () => fetchProcessingPlants() as unknown as Promise<FeatureCollection>,
  install(map: MLMap, data: FeatureCollection, ctx: LayerContext) {
    if (!map.getSource(SRC_ID)) {
      map.addSource(SRC_ID, { type: "geojson", data });
    }

    if (!map.getLayer(CIRCLE_ID)) {
      map.addLayer({
        id: CIRCLE_ID,
        type: "circle",
        source: SRC_ID,
        paint: {
          "circle-radius": 8,
          "circle-color": COLOR_EXPR,
          "circle-opacity": 0.85,
          "circle-stroke-color": "#7dd3fc", // sky-300 — light cyan ring
          "circle-stroke-width": 1.5,
        },
      });
    }

    map.on("mouseenter", CIRCLE_ID, () => {
      map.getCanvas().style.cursor = "pointer";
    });
    map.on("mouseleave", CIRCLE_ID, () => {
      map.getCanvas().style.cursor = "";
    });

    map.on("click", CIRCLE_ID, (e) => {
      const f = e.features?.[0];
      if (!f) return;
      ctx.onSelect({
        kind: "processing_plant",
        props: f.properties as unknown as ProcessingPlantProperties,
      });
    });
  },
};
