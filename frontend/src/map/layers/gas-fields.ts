import type { Map as MLMap } from "maplibre-gl";
import type { FeatureCollection } from "geojson";
import { fetchGasFields } from "@/api/gas-fields";
import type { LayerConfig, LayerContext } from "../LayerRegistry";
import type { GasFieldProperties } from "@/types/geojson";

const SRC_ID = "gas-fields-src";
const CIRCLE_ID = "gas-fields-circle";

const STATUS_COLOR: Record<string, string> = {
  operating: "#34d399",
  construction: "#f59e0b",
  proposed: "#94a3b8",
  idle: "#64748b",
  retired: "#475569",
  unknown: "#6b7280",
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

export const gasFieldsLayer: LayerConfig = {
  id: "gas_fields",
  label: "Gas Fields",
  layerIds: [CIRCLE_ID],
  searchable: true,
  fetch: () => fetchGasFields() as unknown as Promise<FeatureCollection>,
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
          "circle-radius": 7,
          "circle-color": COLOR_EXPR,
          "circle-opacity": 0.85,
          "circle-stroke-color": "#0a0a0a",
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
        kind: "gas_field",
        props: f.properties as unknown as GasFieldProperties,
      });
    });
  },
};
