import type { Map as MLMap } from "maplibre-gl";
import type { FeatureCollection } from "geojson";
import { fetchFlareEvents } from "@/api/flare-events";
import type { LayerConfig, LayerContext } from "../LayerRegistry";
import type { FlareEventProperties } from "@/types/geojson";

const SRC_ID = "flare-events-src";
const HEAT_ID = "flare-events-heat";
const POINT_ID = "flare-events-point";

// Heatmap underneath, individual points on top — points become click targets
// at higher zoom and the heatmap reads the country-scale density at low zoom.
const HEAT_COLOR = [
  "interpolate",
  ["linear"],
  ["heatmap-density"],
  0, "rgba(0, 0, 0, 0)",
  0.2, "rgba(255, 200, 80, 0.35)",
  0.5, "rgba(255, 130, 40, 0.65)",
  0.8, "rgba(255, 60, 20, 0.85)",
  1.0, "rgba(255, 30, 0, 0.95)",
] as unknown as never;

const POINT_COLOR = [
  "case",
  ["==", ["get", "daynight"], "N"], "#ff6b35", // night → orange (more likely flare)
  ["==", ["get", "daynight"], "D"], "#fbbf24", // day → amber (could be either)
  "#f59e0b",
] as unknown as never;

const POINT_RADIUS = [
  "interpolate",
  ["linear"],
  ["coalesce", ["get", "frp"], 0],
  0, 2,
  10, 3,
  50, 5,
  200, 7,
] as unknown as never;

export const flareEventsLayer: LayerConfig = {
  id: "flare_events",
  label: "Flare Detections (VIIRS)",
  layerIds: [HEAT_ID, POINT_ID],
  fetch: () => fetchFlareEvents(14) as unknown as Promise<FeatureCollection>,
  install(map: MLMap, data: FeatureCollection, ctx: LayerContext) {
    if (!map.getSource(SRC_ID)) {
      map.addSource(SRC_ID, { type: "geojson", data });
    }

    if (!map.getLayer(HEAT_ID)) {
      map.addLayer({
        id: HEAT_ID,
        type: "heatmap",
        source: SRC_ID,
        maxzoom: 9,
        paint: {
          "heatmap-weight": [
            "interpolate", ["linear"], ["coalesce", ["get", "frp"], 0],
            0, 0.1, 50, 0.6, 200, 1.0,
          ] as unknown as never,
          "heatmap-intensity": [
            "interpolate", ["linear"], ["zoom"], 0, 0.6, 9, 1.4,
          ] as unknown as never,
          "heatmap-color": HEAT_COLOR,
          "heatmap-radius": [
            "interpolate", ["linear"], ["zoom"], 0, 8, 9, 24,
          ] as unknown as never,
          "heatmap-opacity": [
            "interpolate", ["linear"], ["zoom"], 7, 0.85, 9, 0.4,
          ] as unknown as never,
        },
      });
    }

    if (!map.getLayer(POINT_ID)) {
      map.addLayer({
        id: POINT_ID,
        type: "circle",
        source: SRC_ID,
        minzoom: 6,
        paint: {
          "circle-radius": POINT_RADIUS,
          "circle-color": POINT_COLOR,
          "circle-opacity": 0.9,
          "circle-stroke-color": "#0a0a0a",
          "circle-stroke-width": 0.8,
        },
      });
    }

    map.on("mouseenter", POINT_ID, () => {
      map.getCanvas().style.cursor = "pointer";
    });
    map.on("mouseleave", POINT_ID, () => {
      map.getCanvas().style.cursor = "";
    });

    map.on("click", POINT_ID, (e) => {
      const f = e.features?.[0];
      if (!f) return;
      ctx.onSelect({
        kind: "flare_event",
        props: f.properties as unknown as FlareEventProperties,
      });
    });
  },
};
