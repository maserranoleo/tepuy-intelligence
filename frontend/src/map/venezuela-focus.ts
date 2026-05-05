import type { Map as MLMap } from "maplibre-gl";
import type { Feature, FeatureCollection, Polygon } from "geojson";

const SOURCE_ID = "venezuela-focus-src";
const LAYER_ID = "venezuela-focus-mask";

/**
 * World rectangle. Web Mercator caps at ~85° latitude; staying inside that
 * range avoids polar rendering quirks.
 */
const WORLD_RING: [number, number][] = [
  [-180, -85],
  [180, -85],
  [180, 85],
  [-180, 85],
  [-180, -85],
];

/**
 * Install a country-focus dimming mask: a fill polygon covering the world
 * with a hole punched out for Venezuela's boundary. Drawn above the basemap
 * but below all data layers, so the basemap dims and your data still pops.
 *
 * Idempotent — calling twice on the same map is a no-op.
 *
 * @param map      MapLibre map instance.
 * @param opacity  Mask opacity (0..1). 0.55 reads like a clear focus without
 *                 making neighboring countries unreadable.
 */
export async function installVenezuelaFocus(
  map: MLMap,
  opacity = 0.55
): Promise<void> {
  if (map.getLayer(LAYER_ID)) return;

  let venezuelaRing: [number, number][] | undefined;
  try {
    const res = await fetch("/data/venezuela.geojson");
    if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
    const fc = (await res.json()) as FeatureCollection<Polygon>;
    venezuelaRing = fc.features[0]?.geometry.coordinates[0] as [number, number][];
  } catch (err) {
    console.warn("venezuela-focus: failed to load boundary, skipping mask", err);
    return;
  }

  if (!venezuelaRing || venezuelaRing.length < 4) {
    console.warn("venezuela-focus: empty/invalid boundary, skipping mask");
    return;
  }

  const maskFeature: Feature<Polygon> = {
    type: "Feature",
    properties: {},
    geometry: {
      type: "Polygon",
      // First ring = outer (world), subsequent ring(s) = holes.
      coordinates: [WORLD_RING, venezuelaRing],
    },
  };

  if (!map.getSource(SOURCE_ID)) {
    map.addSource(SOURCE_ID, { type: "geojson", data: maskFeature });
  }

  map.addLayer({
    id: LAYER_ID,
    type: "fill",
    source: SOURCE_ID,
    paint: {
      "fill-color": "#000",
      "fill-opacity": opacity,
      "fill-antialias": false,
    },
  });
}
