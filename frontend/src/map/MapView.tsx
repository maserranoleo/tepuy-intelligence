import { useEffect, useRef } from "react";
import maplibregl, { Map as MLMap } from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import { LayerRegistry } from "./LayerRegistry";
import { pipelinesLayer } from "./layers/pipelines";
import type { PipelineProperties } from "@/types/geojson";

const VEN_BOUNDS: [[number, number], [number, number]] = [
  [-73.5, 0.5],
  [-59.5, 13.0],
];

const STYLE_URL = "https://tiles.openfreemap.org/styles/dark";

type Props = {
  onSelect: (p: PipelineProperties) => void;
};

export default function MapView({ onSelect }: Props) {
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
      const registry = new LayerRegistry(map, [pipelinesLayer]);
      await registry.installAll<PipelineProperties>({ onSelect });
    });

    mapRef.current = map;
    return () => {
      map.remove();
      mapRef.current = null;
    };
  }, [onSelect]);

  return <div ref={containerRef} className="h-full w-full" />;
}
