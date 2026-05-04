import type { Map as MLMap, GeoJSONSource } from "maplibre-gl";
import type { FeatureCollection } from "geojson";

/**
 * A LayerConfig describes one layer end-to-end:
 *   - how to fetch its FeatureCollection,
 *   - the MapLibre source/layer ids,
 *   - the install function (adds source + paint layers + click handlers).
 *
 * Adding a new layer = appending a config object to `layers` in App.tsx.
 */
export type LayerConfig<P extends object = Record<string, unknown>> = {
  id: string;
  label: string;
  fetch: () => Promise<FeatureCollection>;
  /** Install source + style layers on the map. Return cleanup if needed. */
  install: (map: MLMap, data: FeatureCollection, ctx: LayerContext<P>) => void;
};

export type LayerContext<P extends object> = {
  onSelect: (props: P) => void;
};

export class LayerRegistry {
  constructor(private map: MLMap, private layers: LayerConfig[]) {}

  async installAll<P extends object>(ctx: LayerContext<P>): Promise<void> {
    for (const cfg of this.layers) {
      const data = await cfg.fetch();
      cfg.install(this.map, data, ctx as LayerContext<object>);
    }
  }

  async refresh(id: string): Promise<void> {
    const cfg = this.layers.find((l) => l.id === id);
    if (!cfg) return;
    const data = await cfg.fetch();
    const src = this.map.getSource(`${id}-src`) as GeoJSONSource | undefined;
    if (src) src.setData(data);
  }
}
