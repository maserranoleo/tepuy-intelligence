import type { Map as MLMap, GeoJSONSource } from "maplibre-gl";
import type { FeatureCollection } from "geojson";
import type { SelectedEntity } from "@/types/geojson";

export type OnSelect = (sel: SelectedEntity) => void;

export type LayerContext = {
  onSelect: OnSelect;
};

/**
 * A LayerConfig describes one entity layer end-to-end:
 *   - how to fetch its FeatureCollection,
 *   - the MapLibre layer ids it installs (so visibility can toggle them as a unit),
 *   - the install function (adds source + paint layers + click handlers).
 *
 * Adding a new layer = appending a config object to the registry in MapView.
 */
export type LayerConfig = {
  id: string;
  label: string;
  /** Every MapLibre layer id this config adds. Used for setVisibility. */
  layerIds: string[];
  fetch: () => Promise<FeatureCollection>;
  install: (map: MLMap, data: FeatureCollection, ctx: LayerContext) => void;
};

export class LayerRegistry {
  constructor(private map: MLMap, private layers: LayerConfig[]) {}

  list(): LayerConfig[] {
    return this.layers;
  }

  async installAll(ctx: LayerContext): Promise<void> {
    for (const cfg of this.layers) {
      const data = await cfg.fetch();
      cfg.install(this.map, data, ctx);
    }
  }

  async refresh(id: string): Promise<void> {
    const cfg = this.layers.find((l) => l.id === id);
    if (!cfg) return;
    const data = await cfg.fetch();
    const src = this.map.getSource(`${id}-src`) as GeoJSONSource | undefined;
    if (src) src.setData(data);
  }

  setVisibility(id: string, visible: boolean): void {
    const cfg = this.layers.find((l) => l.id === id);
    if (!cfg) return;
    const value = visible ? "visible" : "none";
    for (const layerId of cfg.layerIds) {
      if (this.map.getLayer(layerId)) {
        this.map.setLayoutProperty(layerId, "visibility", value);
      }
    }
  }
}
