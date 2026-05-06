import { useEffect, useRef } from "react";
import maplibregl, { Map as MLMap } from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import { LayerRegistry, type OnSelect } from "./LayerRegistry";
import { pipelinesLayer } from "./layers/pipelines";
import { gasFieldsLayer } from "./layers/gas-fields";
import { processingPlantsLayer } from "./layers/processing-plants";
import { flareEventsLayer } from "./layers/flare-events";
import { installVenezuelaFocus } from "./venezuela-focus";

const VEN_BOUNDS: [[number, number], [number, number]] = [
  [-73.5, 0.5],
  [-59.5, 13.0],
];

const STYLE_URL = "https://tiles.openfreemap.org/styles/dark";

type Props = {
  onSelect: OnSelect;
  /** Called once after the registry is ready, so the parent can drive
   *  layer-visibility toggles via registry.setVisibility. */
  onRegistryReady?: (registry: LayerRegistry) => void;
  /** Live search query; non-empty filters every searchable layer. */
  searchQuery?: string;
  /** Called after each setSearch with the total match count across
   *  searchable layers — drives the "N results" badge. */
  onSearchResultCount?: (count: number | null) => void;
};

export default function MapView({
  onSelect,
  onRegistryReady,
  searchQuery = "",
  onSearchResultCount,
}: Props) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<MLMap | null>(null);
  const registryRef = useRef<LayerRegistry | null>(null);

  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;

    const map = new maplibregl.Map({
      container: containerRef.current,
      style: STYLE_URL,
      bounds: VEN_BOUNDS,
      fitBoundsOptions: { padding: 32 },
      attributionControl: { compact: true, customAttribution: "GEM GGIT · manual_seed" },
    });

    map.addControl(
      new maplibregl.NavigationControl({ showCompass: false }),
      "top-right"
    );

    map.on("load", async () => {
      // Country-focus mask FIRST, so it sits between basemap and data layers.
      // The mask dims the basemap (and basemap labels) outside Venezuela;
      // data layers added afterwards stay at full brightness.
      await installVenezuelaFocus(map);

      // Order matters: flare heatmap underneath, then pipelines, then gas
      // fields, then plants on top (plants are big "infrastructure of
      // interest" markers — keep clicks prioritized for them over fields).
      const registry = new LayerRegistry(map, [
        flareEventsLayer,
        pipelinesLayer,
        gasFieldsLayer,
        processingPlantsLayer,
      ]);
      await registry.installAll({ onSelect });
      registryRef.current = registry;

      // Apply current search if the user already typed before install finished.
      if (searchQuery) {
        const count = registry.setSearch(searchQuery);
        onSearchResultCount?.(count);
      }

      onRegistryReady?.(registry);
    });

    mapRef.current = map;
    return () => {
      map.remove();
      mapRef.current = null;
      registryRef.current = null;
    };
    // intentionally only re-run on mount — registry stays bound to this map
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // React to live searchQuery changes after the registry is ready.
  useEffect(() => {
    const registry = registryRef.current;
    if (!registry) return;
    const count = registry.setSearch(searchQuery);
    onSearchResultCount?.(searchQuery ? count : null);
  }, [searchQuery, onSearchResultCount]);

  return <div ref={containerRef} className="h-full w-full" />;
}
