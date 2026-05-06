import type {
  Annotation,
  AnnotationCreate,
  AnnotationEntityKind,
} from "@/types/annotations";

const BASE = import.meta.env.VITE_API_BASE ?? "http://localhost:8000";

export async function listAnnotations(
  entityKind: AnnotationEntityKind,
  entityId: string
): Promise<Annotation[]> {
  const url =
    `${BASE}/api/annotations` +
    `?entity_kind=${encodeURIComponent(entityKind)}` +
    `&entity_id=${encodeURIComponent(entityId)}`;
  const res = await fetch(url);
  if (!res.ok) throw new Error(`${res.status} ${res.statusText} for ${url}`);
  return res.json() as Promise<Annotation[]>;
}

export async function createAnnotation(
  payload: AnnotationCreate
): Promise<Annotation> {
  const res = await fetch(`${BASE}/api/annotations`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`${res.status} ${res.statusText}: ${text || "create failed"}`);
  }
  return res.json() as Promise<Annotation>;
}

export async function deleteAnnotation(id: string): Promise<void> {
  const res = await fetch(`${BASE}/api/annotations/${id}`, {
    method: "DELETE",
  });
  if (!res.ok && res.status !== 204) {
    throw new Error(`${res.status} ${res.statusText} for delete ${id}`);
  }
}
