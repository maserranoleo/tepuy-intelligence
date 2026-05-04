import { useCallback, useState } from "react";
import MapView from "./map/MapView";
import DetailPanel from "./components/DetailPanel";
import type { PipelineProperties } from "@/types/geojson";

export default function App() {
  const [selected, setSelected] = useState<PipelineProperties | null>(null);

  const onSelect = useCallback((p: PipelineProperties) => setSelected(p), []);
  const onClose = useCallback(() => setSelected(null), []);

  return (
    <div className="relative h-full w-full">
      <header className="absolute top-0 left-0 z-10 flex items-center gap-3 px-5 py-3">
        <div className="rounded border border-neutral-800 bg-neutral-950/85 px-3 py-1.5 backdrop-blur">
          <div className="text-xs uppercase tracking-[0.2em] text-neutral-500">
            Tepuy Gas Intelligence
          </div>
          <div className="text-sm font-medium text-neutral-200">
            Venezuela · Pipelines
          </div>
        </div>
        <Legend />
      </header>

      <MapView onSelect={onSelect} />
      <DetailPanel selected={selected} onClose={onClose} />
    </div>
  );
}

function Legend() {
  const items: { label: string; color: string; dash?: string }[] = [
    { label: "Operating", color: "#34d399" },
    { label: "Construction", color: "#f59e0b", dash: "2 1.5" },
    { label: "Proposed", color: "#94a3b8", dash: "1 2" },
    { label: "Idle", color: "#64748b" },
    { label: "Retired", color: "#475569", dash: "0.5 2" },
  ];
  return (
    <div className="rounded border border-neutral-800 bg-neutral-950/85 px-3 py-2 text-xs backdrop-blur">
      <div className="mb-1 uppercase tracking-wider text-neutral-500">Status</div>
      <div className="flex flex-wrap gap-x-3 gap-y-1">
        {items.map((it) => (
          <div key={it.label} className="flex items-center gap-1.5">
            <svg width="22" height="6" aria-hidden>
              <line
                x1="1"
                y1="3"
                x2="21"
                y2="3"
                stroke={it.color}
                strokeWidth="2"
                strokeDasharray={it.dash}
                strokeLinecap="round"
              />
            </svg>
            <span className="text-neutral-300">{it.label}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
