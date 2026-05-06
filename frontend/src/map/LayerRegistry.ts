import type { Map as MLMap, GeoJSONSource } from "maplibre-gl";
import type { Feature, FeatureCollection } from "geojson";
import type { SelectedEntity } from "@/types/geojson";

export type OnSelect = (sel: SelectedEntity) => void;

export type LayerContext = {
  onSelect: OnSelect;
};

export type MatchFn = (
  props: Record<string, unknown>,
  query: string
) => boolean;

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
  /** Layers that opt into the global search filter. Default: false. */
  searchable?: boolean;
  /** Custom match predicate; defaults to substring across name / name_es /
   *  operator / aliases. */
  match?: MatchFn;
};

const defaultMatch: MatchFn = (props, query) => {
  if (!query) return true;
  const q = query.toLowerCase();
  const aliases = Array.isArray(props.aliases) ? (props.aliases as unknown[]) : [];
  const haystacks: unknown[] = [
    props.name,
    props.name_es,
    props.operator,
    ...aliases,
  ];
  return haystacks.some(
    (h) => typeof h === "string" && h.toLowerCase().includes(q)
  );
};

export class LayerRegistry {
  private dataCache = new Map<string, FeatureCollection>();

  constructor(private map: MLMap, private layers: LayerConfig[]) {}

  list(): LayerConfig[] {
    return this.layers;
  }

  async installAll(ctx: LayerContext): Promise<void> {
    for (const cfg of this.layers) {
      const data = await cfg.fetch();
      this.dataCache.set(cfg.id, data);
      cfg.install(this.map, data, ctx);
    }
  }

  async refresh(id: string): Promise<void> {
    const cfg = this.layers.find((l) => l.id === id);
    if (!cfg) return;
    const data = await cfg.fetch();
    this.dataCache.set(id, data);
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

  /**
   * Filter every searchable layer by the query. Empty query restores the
   * unfiltered cached data. Returns the total matched count across
   * searchable layers (for an "N results" badge).
   */
  setSearch(query: string): number {
    let total = 0;
    for (const cfg of this.layers) {
      if (!cfg.searchable) continue;
      const original = this.dataCache.get(cfg.id);
      if (!original) continue;
      const src = this.map.getSource(`${cfg.id}-src`) as GeoJSONSource | undefined;
      if (!src) continue;

      const match = cfg.match ?? defaultMatch;
      let next: FeatureCollection;
      if (!query) {
        next = original;
      } else {
        const features = original.features.filter((f: Feature) =>
          match((f.properties ?? {}) as Record<string, unknown>, query)
        );
        next = { type: "FeatureCollection", features };
      }
      src.setData(next);
      total += next.features.length;
    }
    return total;
  }
}
