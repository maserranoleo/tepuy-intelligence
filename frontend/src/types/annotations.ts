export type Severity = "info" | "watch" | "risk";
export type AnnotationEntityKind = "pipeline" | "gas_field" | "processing_plant";

export type Annotation = {
  id: string;
  entity_kind: AnnotationEntityKind;
  entity_id: string;
  body: string;
  severity: Severity;
  created_at: string;
};

export type AnnotationCreate = {
  entity_kind: AnnotationEntityKind;
  entity_id: string;
  body: string;
  severity: Severity;
};
