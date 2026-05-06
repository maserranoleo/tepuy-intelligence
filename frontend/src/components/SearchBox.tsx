type Props = {
  value: string;
  onChange: (next: string) => void;
  /** Total matched features across searchable layers. null = no active query. */
  resultCount: number | null;
};

export default function SearchBox({ value, onChange, resultCount }: Props) {
  return (
    <div className="flex items-center gap-2 rounded border border-neutral-800 bg-neutral-950/85 px-2 py-1 backdrop-blur">
      <span className="text-neutral-500" aria-hidden>
        ⌕
      </span>
      <input
        type="text"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder="Search pipelines, fields, plants…"
        className="w-56 bg-transparent text-sm text-neutral-200 placeholder:text-neutral-600 focus:outline-none"
        spellCheck={false}
      />
      {resultCount !== null && (
        <span
          className={`shrink-0 rounded px-1.5 py-0.5 text-xs tabular-nums ${
            resultCount === 0
              ? "bg-red-500/15 text-red-300"
              : "bg-neutral-800 text-neutral-300"
          }`}
        >
          {resultCount} result{resultCount === 1 ? "" : "s"}
        </span>
      )}
      {value && (
        <button
          type="button"
          onClick={() => onChange("")}
          className="shrink-0 rounded px-1 text-sm text-neutral-500 hover:text-neutral-200"
          aria-label="Clear search"
        >
          ✕
        </button>
      )}
    </div>
  );
}
