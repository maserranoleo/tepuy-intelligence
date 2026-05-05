import { useEffect, useRef } from "react";
import maplibregl, { Map as MLMap } from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import { LayerRegistry, type OnSelect } from "./LayerRegistry";
import { pipelinesLayer } from "./layers/pipelines";
import { gasFieldsLayer } from "./layers/gas-fields";
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
};

export default function MapView({ onSelect, onRegistryReady }: Props) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<MLMap | null>(null);

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
      // fields and flare points on top so their click handlers take priority.
      const registry = new LayerRegistry(map, [
        flareEventsLayer,
        pipelinesLayer,
        gasFieldsLayer,
      ]);
      await registry.installAll({ onSelect });
      onRegistryReady?.(registry);
    });

    mapRef.current = map;
    return () => {
      map.remove();
      mapRef.current = null;
    };
  }, [onSelect, onRegistryReady]);

  return <div ref={containerRef} className="h-full w-full" />;
}
