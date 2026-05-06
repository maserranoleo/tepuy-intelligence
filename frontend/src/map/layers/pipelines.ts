import type { Map as MLMap } from "maplibre-gl";
import type { FeatureCollection } from "geojson";
import { fetchPipelines } from "@/api/pipelines";
import type { LayerConfig, LayerContext } from "../LayerRegistry";
import type { PipelineProperties } from "@/types/geojson";

const SRC_ID = "pipelines-src";
const LINE_ID = "pipelines-line";
const HALO_ID = "pipelines-halo";

// status → color
const STATUS_COLOR: Record<string, string> = {
  operating: "#34d399", // emerald
  construction: "#f59e0b", // amber
  proposed: "#94a3b8", // slate
  idle: "#64748b", // slate-dim
  retired: "#475569", // slate-darker
  unknown: "#6b7280", // grey
};

// MapLibre expression types are awkward to import; cast to unknown.
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

const DASH_EXPR = [
  "match",
  ["get", "status"],
  "construction", ["literal", [2, 1.5]],
  "proposed", ["literal", [1, 2]],
  "retired", ["literal", [0.5, 2]],
  ["literal", [1]],
] as unknown as never;

export const pipelinesLayer: LayerConfig = {
  id: "pipelines",
  label: "Gas Pipelines",
  layerIds: [HALO_ID, LINE_ID],
  searchable: true,
  fetch: () => fetchPipelines() as unknown as Promise<FeatureCollection>,
  install(map: MLMap, data: FeatureCollection, ctx: LayerContext) {
    if (!map.getSource(SRC_ID)) {
      map.addSource(SRC_ID, { type: "geojson", data });
    }

    if (!map.getLayer(HALO_ID)) {
      map.addLayer({
        id: HALO_ID,
        type: "line",
        source: SRC_ID,
        paint: {
          "line-color": COLOR_EXPR,
          "line-width": 6,
          "line-opacity": 0.18,
          "line-blur": 2,
        },
      });
    }

    if (!map.getLayer(LINE_ID)) {
      map.addLayer({
        id: LINE_ID,
        type: "line",
        source: SRC_ID,
        layout: { "line-cap": "round", "line-join": "round" },
        paint: {
          "line-color": COLOR_EXPR,
          "line-width": 2.2,
          "line-dasharray": DASH_EXPR,
        },
      });
    }

    map.on("mouseenter", LINE_ID, () => {
      map.getCanvas().style.cursor = "pointer";
    });
    map.on("mouseleave", LINE_ID, () => {
      map.getCanvas().style.cursor = "";
    });

    map.on("click", LINE_ID, (e) => {
      const f = e.features?.[0];
      if (!f) return;
      ctx.onSelect({
        kind: "pipeline",
        props: f.properties as unknown as PipelineProperties,
      });
    });
  },
};
