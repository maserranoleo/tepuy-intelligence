import type {
  EntityCommon,
  FlareEventProperties,
  FlareProximity,
  GasFieldProperties,
  PipelineProperties,
  ProcessingPlantProperties,
  SanctionsMatch,
  SelectedEntity,
  Source,
} from "@/types/geojson";

type Props = {
  selected: SelectedEntity | null;
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

const KIND_LABEL: Record<SelectedEntity["kind"], string> = {
  pipeline: "Pipeline",
  gas_field: "Gas Field",
  processing_plant: "Processing Plant",
  flare_event: "Flare Detection",
};

const PLANT_TYPE_LABEL: Record<string, string> = {
  compression: "Compression",
  processing: "Gas Processing",
  cryogenic: "Cryogenic / NGL",
  refinery_gas_treatment: "Refinery Gas Treatment",
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

  if (selected.kind === "flare_event") {
    return <FlareDetailPanel p={selected.props} onClose={onClose} />;
  }

  const props = selected.props;
  const sources = ensureArray(parseMaybe<Source[]>(props.sources));
  const sanctions = ensureArray(parseMaybe<SanctionsMatch[]>(props.sanctions));
  const aliases = ensureArray(parseMaybe<string[]>(props.aliases));
  const externalIds =
    parseMaybe<Record<string, string>>(props.external_ids) ?? {};
  const extra = parseMaybe<Record<string, unknown>>(props.properties) ?? {};

  return (
    <aside className="absolute top-0 right-0 z-20 h-full w-[380px] max-w-[90vw] overflow-y-auto border-l border-neutral-800 bg-neutral-950/95 p-5 backdrop-blur">
      <EntityHeader
        kindLabel={KIND_LABEL[selected.kind]}
        common={props}
        aliases={aliases}
        sanctions={sanctions}
        onClose={onClose}
      />

      {selected.kind === "pipeline" ? (
        <PipelineFields p={props as PipelineProperties} />
      ) : selected.kind === "processing_plant" ? (
        <ProcessingPlantFields
          p={props as ProcessingPlantProperties}
          extra={extra}
        />
      ) : (
        <GasFieldFields p={props as GasFieldProperties} extra={extra} />
      )}

      {(selected.kind === "gas_field" ||
        selected.kind === "processing_plant") && (
        <FlareActivityBlock
          stats={props as unknown as FlareProximity}
        />
      )}

      <NoteBlock extra={extra} />
      <SanctionsBlock sanctions={sanctions} operator={props.operator ?? null} />
      <SourcesList sources={sources} />
      <ExternalIdsList externalIds={externalIds} />
    </aside>
  );
}

function FlareDetailPanel({
  p,
  onClose,
}: {
  p: FlareEventProperties;
  onClose: () => void;
}) {
  const sources = ensureArray(parseMaybe<Source[]>(p.sources));
  const acquired = new Date(p.acquired_at);

  return (
    <aside className="absolute top-0 right-0 z-20 h-full w-[380px] max-w-[90vw] overflow-y-auto border-l border-neutral-800 bg-neutral-950/95 p-5 backdrop-blur">
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="text-xs uppercase tracking-wider text-neutral-500">
            {KIND_LABEL.flare_event}
          </div>
          <h2 className="mt-1 text-lg font-semibold leading-tight">
            {acquired.toISOString().replace("T", " ").slice(0, 16)} UTC
          </h2>
          <div className="mt-0.5 text-xs text-neutral-500">
            {p.satellite ?? "—"} · {p.instrument ?? "—"}
          </div>
        </div>
        <button
          onClick={onClose}
          className="rounded border border-neutral-800 px-2 py-1 text-xs text-neutral-400 hover:border-neutral-600 hover:text-neutral-200"
          aria-label="Close detail panel"
        >
          ✕
        </button>
      </div>

      <dl className="mt-5 grid grid-cols-2 gap-x-4 gap-y-3 text-sm">
        <Field
          label="FRP"
          value={formatNumber(p.frp, "MW")}
        />
        <Field
          label="Confidence"
          value={p.confidence ?? null}
        />
        <Field
          label="Day / Night"
          value={p.daynight === "N" ? "Night" : p.daynight === "D" ? "Day" : null}
        />
        <Field label="Bright TI4" value={formatNumber(p.brightness_ti4, "K")} />
      </dl>

      <div className="mt-5 border-t border-neutral-800 pt-4 text-sm text-neutral-400 leading-snug">
        Single satellite detection — could be a gas flare or a wildfire. Flares
        show <span className="text-neutral-200">at the same coordinates day after day</span>;
        wildfires move. Use the date range and the heat-map view to judge
        persistence.
      </div>

      <SourcesList sources={sources} />

      <div className="mt-5 border-t border-neutral-800 pt-4 text-xs text-neutral-500 font-mono">
        <div className="uppercase tracking-wider font-sans">Detection ID</div>
        <div className="mt-1 break-all text-neutral-300">{p.external_id}</div>
      </div>
    </aside>
  );
}

function EntityHeader({
  kindLabel,
  common,
  aliases,
  sanctions,
  onClose,
}: {
  kindLabel: string;
  common: EntityCommon;
  aliases: string[];
  sanctions: SanctionsMatch[];
  onClose: () => void;
}) {
  const statusKey = (common.status || "unknown").toLowerCase();
  const badge = STATUS_BADGE[statusKey] ?? STATUS_BADGE.unknown;
  const venezuelaHits = sanctions.filter((s) => s.venezuela_program).length;
  const sanctionsLabel = venezuelaHits > 0 ? "OFAC · VEN" : "OFAC";

  return (
    <>
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="text-xs uppercase tracking-wider text-neutral-500">
            {kindLabel}
          </div>
          <h2 className="mt-1 text-lg font-semibold leading-tight">{common.name}</h2>
          {common.name_es && common.name_es !== common.name && (
            <div className="mt-0.5 text-sm text-neutral-400">{common.name_es}</div>
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
          {common.status}
        </span>
        {common.status_as_of && (
          <span className="text-xs text-neutral-500">
            as of {new Date(common.status_as_of).toISOString().slice(0, 10)}
          </span>
        )}
        {sanctions.length > 0 && (
          <span
            title={`${sanctions.length} potential SDN match${sanctions.length === 1 ? "" : "es"}`}
            className="rounded border border-red-500/40 bg-red-500/15 px-2 py-0.5 text-xs uppercase tracking-wider text-red-300"
          >
            ⚠ {sanctionsLabel} · {sanctions.length}
          </span>
        )}
      </div>
    </>
  );
}

function PipelineFields({ p }: { p: PipelineProperties }) {
  return (
    <dl className="mt-5 grid grid-cols-2 gap-x-4 gap-y-3 text-sm">
      <Field label="Length" value={formatNumber(p.length_km, "km")} />
      <Field label="Diameter" value={formatNumber(p.diameter_in, "in")} />
      <Field label="Capacity" value={formatNumber(p.capacity_mmcfd, "mmcfd")} />
      <Field label="Operator" value={p.operator ?? null} />
    </dl>
  );
}

function ProcessingPlantFields({
  p,
  extra,
}: {
  p: ProcessingPlantProperties;
  extra: Record<string, unknown>;
}) {
  const plantTypeKey =
    typeof extra.plant_type === "string" ? (extra.plant_type as string) : null;
  const plantType = plantTypeKey
    ? PLANT_TYPE_LABEL[plantTypeKey] ?? plantTypeKey
    : null;
  const role = typeof extra.role === "string" ? (extra.role as string) : null;
  const capacityNote =
    typeof extra.capacity_note === "string" ? (extra.capacity_note as string) : null;

  return (
    <dl className="mt-5 grid grid-cols-2 gap-x-4 gap-y-3 text-sm">
      <Field label="Plant Type" value={plantType} />
      <Field label="Operator" value={p.operator ?? null} />
      <Field label="Role" value={role} />
      <Field label="Capacity" value={capacityNote} />
    </dl>
  );
}

function GasFieldFields({
  p,
  extra,
}: {
  p: GasFieldProperties;
  extra: Record<string, unknown>;
}) {
  const reservoirType =
    typeof extra.reservoir_type === "string" ? (extra.reservoir_type as string) : null;
  const reservesEstimate =
    typeof extra.reserves_tcf === "number"
      ? `${(extra.reserves_tcf as number).toLocaleString(undefined, { maximumFractionDigits: 1 })} Tcf`
      : typeof extra.reserves_estimate === "string"
      ? (extra.reserves_estimate as string)
      : null;
  const basin = typeof extra.basin === "string" ? (extra.basin as string) : null;

  return (
    <dl className="mt-5 grid grid-cols-2 gap-x-4 gap-y-3 text-sm">
      <Field label="Operator" value={p.operator ?? null} />
      <Field label="Reservoir" value={reservoirType} />
      <Field label="Basin" value={basin} />
      <Field label="Reserves" value={reservesEstimate} />
    </dl>
  );
}

function FlareActivityBlock({ stats }: { stats: FlareProximity }) {
  const count = Number(stats.recent_flare_count ?? 0);
  const lastSeen = stats.last_flare_at ? new Date(stats.last_flare_at) : null;
  const peakFrp =
    stats.peak_frp_mw !== null && stats.peak_frp_mw !== undefined
      ? Number(stats.peak_frp_mw)
      : null;

  // Heuristic visual tier: 0 = quiet, 1-5 = weak, 6+ = strong signal.
  const tier = count === 0 ? "quiet" : count <= 5 ? "weak" : "strong";
  const styles: Record<typeof tier, string> = {
    quiet: "border-neutral-800 bg-neutral-900/40 text-neutral-400",
    weak: "border-amber-500/40 bg-amber-500/10 text-amber-200",
    strong: "border-emerald-500/40 bg-emerald-500/10 text-emerald-200",
  };
  const headlineStyles: Record<typeof tier, string> = {
    quiet: "text-neutral-300",
    weak: "text-amber-200",
    strong: "text-emerald-200",
  };

  const daysAgo = lastSeen
    ? Math.floor((Date.now() - lastSeen.getTime()) / 86400000)
    : null;

  return (
    <div className={`mt-5 rounded border px-3 py-2.5 text-sm ${styles[tier]}`}>
      <div className="flex items-baseline justify-between">
        <span className="text-xs uppercase tracking-wider opacity-80">
          Flare Activity (5 km · 30 d)
        </span>
        <span className={`text-xl font-semibold tabular-nums ${headlineStyles[tier]}`}>
          {count}
        </span>
      </div>
      {count === 0 ? (
        <p className="mt-1 text-xs leading-snug opacity-80">
          No VIIRS detections within 5 km in the last 30 days. Either the
          asset is quiet, FIRMS hasn't been ingested yet, or the assets's
          coordinates are off.
        </p>
      ) : (
        <div className="mt-1 grid grid-cols-2 gap-x-4 gap-y-1 text-xs">
          <div className="opacity-70">Last seen</div>
          <div className="text-right tabular-nums">
            {daysAgo === 0
              ? "today"
              : daysAgo === 1
              ? "yesterday"
              : `${daysAgo} d ago`}
          </div>
          <div className="opacity-70">Peak FRP</div>
          <div className="text-right tabular-nums">
            {peakFrp !== null
              ? `${peakFrp.toLocaleString(undefined, { maximumFractionDigits: 1 })} MW`
              : "—"}
          </div>
        </div>
      )}
      {count > 5 && (
        <p className="mt-2 text-xs leading-snug opacity-70">
          Persistent thermal signal — strong evidence the asset is operating.
          Single detections can be wildfires; recurrence at one centroid is
          the flare signature.
        </p>
      )}
    </div>
  );
}

function NoteBlock({ extra }: { extra: Record<string, unknown> }) {
  if (!extra.note && !extra.cross_border && !extra.geometry_quality) return null;
  return (
    <div className="mt-5 border-t border-neutral-800 pt-4 text-sm text-neutral-300">
      {Array.isArray(extra.cross_border) &&
        (extra.cross_border as string[]).length > 1 && (
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
  );
}

function SanctionsBlock({
  sanctions,
  operator,
}: {
  sanctions: SanctionsMatch[];
  operator: string | null;
}) {
  if (sanctions.length === 0) return null;

  return (
    <div className="mt-5 border-t border-red-900/40 pt-4">
      <div className="flex items-center gap-2 text-xs uppercase tracking-wider text-red-400">
        <span>⚠ Sanctions exposure</span>
      </div>
      <p className="mt-1 text-xs text-neutral-500 leading-snug">
        Potential OFAC SDN match{sanctions.length === 1 ? "" : "es"} for
        operator{" "}
        {operator ? (
          <span className="text-neutral-300">"{operator}"</span>
        ) : (
          "this entity"
        )}
        . Candidate, not a legal determination — verify against the OFAC
        entry below.
      </p>
      <ul className="mt-2 space-y-2 text-sm">
        {sanctions.map((s) => (
          <li
            key={s.ent_num}
            className={`rounded border px-2.5 py-2 ${
              s.venezuela_program
                ? "border-red-500/40 bg-red-500/10"
                : "border-amber-500/30 bg-amber-500/10"
            }`}
          >
            <div className="flex items-start justify-between gap-2">
              <span className="font-medium text-neutral-100 leading-snug">
                {s.matched_name}
              </span>
              <a
                href={s.ofac_url}
                target="_blank"
                rel="noreferrer"
                className="shrink-0 text-xs text-red-300 underline-offset-2 hover:underline"
              >
                OFAC ↗
              </a>
            </div>
            <div className="mt-1 flex flex-wrap items-center gap-1.5 text-xs text-neutral-400">
              {s.sdn_type && (
                <span className="rounded border border-neutral-700 px-1.5 py-0.5">
                  {s.sdn_type}
                </span>
              )}
              {s.programs.map((p) => (
                <span
                  key={p}
                  className={`rounded border px-1.5 py-0.5 ${
                    /VENEZUELA/i.test(p)
                      ? "border-red-500/40 text-red-300"
                      : "border-neutral-700 text-neutral-400"
                  }`}
                >
                  {p}
                </span>
              ))}
            </div>
            <div className="mt-1 text-xs text-neutral-500">
              matched on:{" "}
              <span className="font-mono text-neutral-400">
                {s.matched_tokens.join(", ")}
              </span>
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}

function SourcesList({ sources }: { sources: Source[] }) {
  return (
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
  );
}

function ExternalIdsList({ externalIds }: { externalIds: Record<string, string> }) {
  if (Object.keys(externalIds).length === 0) return null;
  return (
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
  );
}

function Field({ label, value }: { label: string; value: string | null }) {
  return (
    <div>
      <dt className="text-xs uppercase tracking-wider text-neutral-500">{label}</dt>
      <dd className="mt-0.5 text-neutral-200">
        {value ?? <span className="text-neutral-600">—</span>}
      </dd>
    </div>
  );
}
