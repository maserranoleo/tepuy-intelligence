import type { PipelineProperties, Source } from "@/types/geojson";

type Props = {
  selected: PipelineProperties | null;
  onClose: () => void;
};

const STATUS_BADGE: Record<string, string> = {
  operating: "bg-emerald-500/15 text-emerald-300 border-emerald-500/30",
  construction: "bg-amber-500/15 text-amber-300 border-amber-500/30",
  proposed: "bg-slate-400/15 text-slate-300 border-slate-400/30",
  idle: "bg-slate-500/15 text-slate-400 border-slate-500/30",
  retired: "bg-slate-600/15 text-slate-500 border-slate-600/30",
  unknown: "bg-neutral-500/15 text-neutral-400 border-neutral-500/30",
};

function formatNumber(n: number | null | undefined, suffix: string): string | null {
  if (n === null || n === undefined) return null;
  return `${Number(n).toLocaleString(undefined, { maximumFractionDigits: 1 })} ${suffix}`;
}

function ensureArray<T>(v: T[] | null | undefined): T[] {
  return Array.isArray(v) ? v : [];
}

/** Properties come back from MapLibre features as JSON-strings for nested objects;
 *  fall back gracefully if anything is already parsed. */
function parseMaybe<T>(v: unknown): T | null {
  if (v === null || v === undefined) return null;
  if (typeof v === "string") {
    try {
      return JSON.parse(v) as T;
    } catch {
      return null;
    }
  }
  return v as T;
}

export default function DetailPanel({ selected, onClose }: Props) {
  if (!selected) return null;

  const sources = ensureArray(parseMaybe<Source[]>(selected.sources));
  const aliases = ensureArray(parseMaybe<string[]>(selected.aliases));
  const externalIds =
    parseMaybe<Record<string, string>>(selected.external_ids) ?? {};
  const extra = parseMaybe<Record<string, unknown>>(selected.properties) ?? {};

  const statusKey = (selected.status || "unknown").toLowerCase();
  const badge = STATUS_BADGE[statusKey] ?? STATUS_BADGE.unknown;

  return (
    <aside className="absolute top-0 right-0 z-20 h-full w-[380px] max-w-[90vw] overflow-y-auto border-l border-neutral-800 bg-neutral-950/95 p-5 backdrop-blur">
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="text-xs uppercase tracking-wider text-neutral-500">Pipeline</div>
          <h2 className="mt-1 text-lg font-semibold leading-tight">{selected.name}</h2>
          {selected.name_es && selected.name_es !== selected.name && (
            <div className="mt-0.5 text-sm text-neutral-400">{selected.name_es}</div>
          )}
          {aliases.length > 0 && (
            <div className="mt-1 text-xs text-neutral-500">
              also: {aliases.join(", ")}
            </div>
          )}
        </div>
        <button
          onClick={onClose}
          className="rounded border border-neutral-800 px-2 py-1 text-xs text-neutral-400 hover:border-neutral-600 hover:text-neutral-200"
          aria-label="Close detail panel"
        >
          ✕
        </button>
      </div>

      <div className="mt-3 flex flex-wrap items-center gap-2">
        <span className={`rounded border px-2 py-0.5 text-xs uppercase tracking-wider ${badge}`}>
          {selected.status}
        </span>
        {selected.status_as_of && (
          <span className="text-xs text-neutral-500">
            as of {new Date(selected.status_as_of).toISOString().slice(0, 10)}
          </span>
        )}
      </div>

      <dl className="mt-5 grid grid-cols-2 gap-x-4 gap-y-3 text-sm">
        <Field label="Length" value={formatNumber(selected.length_km, "km")} />
        <Field label="Diameter" value={formatNumber(selected.diameter_in, "in")} />
        <Field label="Capacity" value={formatNumber(selected.capacity_mmcfd, "mmcfd")} />
        <Field label="Operator" value={selected.operator ?? null} />
      </dl>

      {Boolean(extra.note || extra.cross_border) && (
        <div className="mt-5 border-t border-neutral-800 pt-4 text-sm text-neutral-300">
          {Array.isArray(extra.cross_border) && (extra.cross_border as string[]).length > 1 && (
            <div className="mb-2 text-xs uppercase tracking-wider text-neutral-500">
              Cross-border: {(extra.cross_border as string[]).join(" ↔ ")}
            </div>
          )}
          {typeof extra.note === "string" && <p className="leading-snug">{extra.note}</p>}
          {typeof extra.geometry_quality === "string" && (
            <p className="mt-2 text-xs text-neutral-500">
              Geometry: {extra.geometry_quality.replace(/_/g, " ")}
            </p>
          )}
        </div>
      )}

      <div className="mt-5 border-t border-neutral-800 pt-4">
        <div className="text-xs uppercase tracking-wider text-neutral-500">Sources</div>
        {sources.length === 0 ? (
          <p className="mt-2 text-sm text-neutral-400">No sources recorded.</p>
        ) : (
          <ul className="mt-2 space-y-2 text-sm">
            {sources.map((s, i) => (
              <li key={i} className="leading-snug">
                <span className="font-medium text-neutral-200">{s.source_name}</span>
                {s.source_id && (
                  <span className="ml-1 text-neutral-500">[{s.source_id}]</span>
                )}
                {s.url && (
                  <>
                    {" "}
                    <a
                      href={s.url}
                      target="_blank"
                      rel="noreferrer"
                      className="text-emerald-400 underline-offset-2 hover:underline"
                    >
                      link
                    </a>
                  </>
                )}
                {s.note && <div className="text-xs text-neutral-500">{s.note}</div>}
                <div className="text-xs text-neutral-600">
                  retrieved {new Date(s.retrieved_at).toISOString().slice(0, 10)}
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>

      {Object.keys(externalIds).length > 0 && (
        <div className="mt-5 border-t border-neutral-800 pt-4 text-xs text-neutral-500">
          <div className="uppercase tracking-wider">External IDs</div>
          <ul className="mt-1 space-y-0.5 font-mono">
            {Object.entries(externalIds).map(([k, v]) => (
              <li key={k}>
                <span className="text-neutral-400">{k}</span> ={" "}
                <span className="text-neutral-300">{v}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </aside>
  );
}

function Field({ label, value }: { label: string; value: string | null }) {
  return (
    <div>
      <dt className="text-xs uppercase tracking-wider text-neutral-500">{label}</dt>
      <dd className="mt-0.5 text-neutral-200">{value ?? <span className="text-neutral-600">—</span>}</dd>
    </div>
  );
}
