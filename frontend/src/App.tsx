import { useCallback, useState } from "react";
import MapView from "./map/MapView";
import DetailPanel from "./components/DetailPanel";
import type { LayerRegistry } from "./map/LayerRegistry";
import type { SelectedEntity } from "@/types/geojson";

type LayerKey = "pipelines" | "gas_fields" | "flare_events";

export default function App() {
  const [selected, setSelected] = useState<SelectedEntity | null>(null);
  const [registry, setRegistry] = useState<LayerRegistry | null>(null);
  const [visibility, setVisibilityState] = useState<Record<LayerKey, boolean>>({
    pipelines: true,
    gas_fields: true,
    flare_events: true,
  });

  const onSelect = useCallback((sel: SelectedEntity) => setSelected(sel), []);
  const onClose = useCallback(() => setSelected(null), []);

  const toggleLayer = (key: LayerKey, value: boolean) => {
    setVisibilityState((v) => ({ ...v, [key]: value }));
    registry?.setVisibility(key, value);
  };

  return (
    <div className="relative h-full w-full">
      <header className="absolute top-0 left-0 z-10 flex flex-col gap-2 px-5 py-3 sm:flex-row sm:items-start">
        <div className="rounded border border-neutral-800 bg-neutral-950/85 px-3 py-1.5 backdrop-blur">
          <div className="text-xs uppercase tracking-[0.2em] text-neutral-500">
            Tepuy Gas Intelligence
          </div>
          <div className="text-sm font-medium text-neutral-200">
            Venezuela · Gas System
          </div>
        </div>
        <LayerPanel visibility={visibility} onToggle={toggleLayer} />
      </header>

      <MapView onSelect={onSelect} onRegistryReady={setRegistry} />
      <DetailPanel selected={selected} onClose={onClose} />
    </div>
  );
}

type StatusItem = { label: string; color: string; dash?: string };

const PIPELINE_STATUSES: StatusItem[] = [
  { label: "Operating", color: "#34d399" },
  { label: "Construction", color: "#f59e0b", dash: "2 1.5" },
  { label: "Proposed", color: "#94a3b8", dash: "1 2" },
  { label: "Idle", color: "#64748b" },
  { label: "Retired", color: "#475569", dash: "0.5 2" },
];

const GAS_FIELD_STATUSES: StatusItem[] = [
  { label: "Operating", color: "#34d399" },
  { label: "Proposed", color: "#94a3b8" },
  { label: "Idle", color: "#64748b" },
];

const FLARE_KINDS: StatusItem[] = [
  { label: "Night detection", color: "#ff6b35" },
  { label: "Day detection", color: "#fbbf24" },
];

function LayerPanel({
  visibility,
  onToggle,
}: {
  visibility: Record<LayerKey, boolean>;
  onToggle: (key: LayerKey, value: boolean) => void;
}) {
  return (
    <div className="rounded border border-neutral-800 bg-neutral-950/85 px-3 py-2 text-xs backdrop-blur">
      <div className="mb-1 uppercase tracking-wider text-neutral-500">Layers</div>
      <div className="space-y-2">
        <LayerToggleRow
          label="Gas Pipelines"
          checked={visibility.pipelines}
          onChange={(v) => onToggle("pipelines", v)}
        >
          <LineSwatches items={PIPELINE_STATUSES} />
        </LayerToggleRow>
        <LayerToggleRow
          label="Gas Fields"
          checked={visibility.gas_fields}
          onChange={(v) => onToggle("gas_fields", v)}
        >
          <CircleSwatches items={GAS_FIELD_STATUSES} />
        </LayerToggleRow>
        <LayerToggleRow
          label="Flare Detections (VIIRS · 14d)"
          checked={visibility.flare_events}
          onChange={(v) => onToggle("flare_events", v)}
        >
          <CircleSwatches items={FLARE_KINDS} />
          <span className="text-neutral-500">heatmap below z9 · points above</span>
        </LayerToggleRow>
      </div>
    </div>
  );
}

function LayerToggleRow({
  label,
  checked,
  onChange,
  children,
}: {
  label: string;
  checked: boolean;
  onChange: (v: boolean) => void;
  children: React.ReactNode;
}) {
  return (
    <div>
      <label className="flex items-center gap-2 text-neutral-200">
        <input
          type="checkbox"
          checked={checked}
          onChange={(e) => onChange(e.target.checked)}
          className="accent-emerald-500"
        />
        <span className="font-medium">{label}</span>
      </label>
      <div className="ml-6 mt-1 flex flex-wrap gap-x-3 gap-y-1">{children}</div>
    </div>
  );
}

function LineSwatches({ items }: { items: StatusItem[] }) {
  return (
    <>
      {items.map((it) => (
        <div key={it.label} className="flex items-center gap-1.5">
          <svg width="22" height="6" aria-hidden>
            <line
              x1="1" y1="3" x2="21" y2="3"
              stroke={it.color}
              strokeWidth="2"
              strokeDasharray={it.dash}
              strokeLinecap="round"
            />
          </svg>
          <span className="text-neutral-400">{it.label}</span>
        </div>
      ))}
    </>
  );
}

function CircleSwatches({ items }: { items: StatusItem[] }) {
  return (
    <>
      {items.map((it) => (
        <div key={it.label} className="flex items-center gap-1.5">
          <svg width="14" height="10" aria-hidden>
            <circle cx="7" cy="5" r="4" fill={it.color} stroke="#0a0a0a" strokeWidth="1" />
          </svg>
          <span className="text-neutral-400">{it.label}</span>
        </div>
      ))}
    </>
  );
}
