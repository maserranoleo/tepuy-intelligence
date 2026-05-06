import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  createAnnotation,
  deleteAnnotation,
  listAnnotations,
} from "@/api/annotations";
import type {
  Annotation,
  AnnotationEntityKind,
  Severity,
} from "@/types/annotations";

type Props = {
  entityKind: AnnotationEntityKind;
  entityId: string;
};

const SEVERITY_STYLES: Record<Severity, string> = {
  info: "border-neutral-700 bg-neutral-800/40 text-neutral-300",
  watch: "border-amber-500/40 bg-amber-500/10 text-amber-200",
  risk: "border-red-500/40 bg-red-500/10 text-red-300",
};

const SEVERITY_LABEL: Record<Severity, string> = {
  info: "Info",
  watch: "Watch",
  risk: "Risk",
};

export default function AnnotationsBlock({ entityKind, entityId }: Props) {
  const qc = useQueryClient();
  const queryKey = ["annotations", entityKind, entityId];

  const { data: annotations = [], isLoading, error } = useQuery({
    queryKey,
    queryFn: () => listAnnotations(entityKind, entityId),
    staleTime: 0,
  });

  const create = useMutation({
    mutationFn: createAnnotation,
    onSuccess: () => qc.invalidateQueries({ queryKey }),
  });

  const remove = useMutation({
    mutationFn: deleteAnnotation,
    onSuccess: () => qc.invalidateQueries({ queryKey }),
  });

  const [body, setBody] = useState("");
  const [severity, setSeverity] = useState<Severity>("info");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = body.trim();
    if (!trimmed) return;
    create.mutate(
      { entity_kind: entityKind, entity_id: entityId, body: trimmed, severity },
      {
        onSuccess: () => {
          setBody("");
          setSeverity("info");
        },
      }
    );
  };

  return (
    <div className="mt-5 border-t border-neutral-800 pt-4">
      <div className="flex items-center justify-between">
        <span className="text-xs uppercase tracking-wider text-neutral-500">
          Notes
        </span>
        <span className="text-xs text-neutral-600">
          {isLoading ? "…" : `${annotations.length}`}
        </span>
      </div>

      {error instanceof Error && (
        <div className="mt-2 text-xs text-red-300">
          Failed to load notes: {error.message}
        </div>
      )}

      {annotations.length > 0 && (
        <ul className="mt-2 space-y-2">
          {annotations.map((a) => (
            <AnnotationRow
              key={a.id}
              annotation={a}
              onDelete={() => remove.mutate(a.id)}
              deleting={remove.isPending && remove.variables === a.id}
            />
          ))}
        </ul>
      )}

      <form onSubmit={handleSubmit} className="mt-3 space-y-2">
        <textarea
          value={body}
          onChange={(e) => setBody(e.target.value)}
          placeholder="Add a note (max 2000 chars)…"
          rows={3}
          maxLength={2000}
          className="w-full resize-y rounded border border-neutral-800 bg-neutral-900 px-2 py-1.5 text-sm text-neutral-200 placeholder:text-neutral-600 focus:border-neutral-600 focus:outline-none"
          disabled={create.isPending}
        />
        <div className="flex items-center gap-2">
          <select
            value={severity}
            onChange={(e) => setSeverity(e.target.value as Severity)}
            className="rounded border border-neutral-800 bg-neutral-900 px-2 py-1 text-xs text-neutral-300 focus:border-neutral-600 focus:outline-none"
            disabled={create.isPending}
          >
            <option value="info">Info</option>
            <option value="watch">Watch</option>
            <option value="risk">Risk</option>
          </select>
          <button
            type="submit"
            className="rounded border border-neutral-700 bg-neutral-800 px-3 py-1 text-xs font-medium text-neutral-200 hover:border-neutral-500 disabled:opacity-50"
            disabled={!body.trim() || create.isPending}
          >
            {create.isPending ? "Saving…" : "Add Note"}
          </button>
          {create.isError && (
            <span className="text-xs text-red-300">
              {(create.error as Error).message}
            </span>
          )}
        </div>
      </form>
    </div>
  );
}

function AnnotationRow({
  annotation: a,
  onDelete,
  deleting,
}: {
  annotation: Annotation;
  onDelete: () => void;
  deleting: boolean;
}) {
  const style = SEVERITY_STYLES[a.severity] ?? SEVERITY_STYLES.info;
  return (
    <li className={`rounded border px-2.5 py-2 ${style}`}>
      <div className="flex items-start justify-between gap-2">
        <span className="text-xs uppercase tracking-wider opacity-80">
          {SEVERITY_LABEL[a.severity]}
        </span>
        <button
          onClick={onDelete}
          disabled={deleting}
          aria-label="Delete note"
          className="text-xs text-neutral-500 hover:text-neutral-300 disabled:opacity-50"
        >
          {deleting ? "…" : "✕"}
        </button>
      </div>
      <p className="mt-1 whitespace-pre-wrap break-words text-sm leading-snug">
        {a.body}
      </p>
      <div className="mt-1 text-xs opacity-60">
        {new Date(a.created_at).toLocaleString()}
      </div>
    </li>
  );
}
