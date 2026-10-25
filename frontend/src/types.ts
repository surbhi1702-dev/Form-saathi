export type Lang = "en" | "ta" | "hi" | "or";
export type InputMode = "text" | "voice" | "tap";

export interface FormCard {
  id: string;
  category: string;
  title: string;
  description: string;
  department: string;
  question_count: number;
}

export interface ChatMessage {
  role: "user" | "assistant";
  text: string;
  sources?: string[];
}

export interface FieldView {
  id: string;
  label: string;
  status: "filled" | "skipped" | "current" | "pending";
  value: string | null;
  required: boolean;
  type: string;
}

export interface CurrentQuestion {
  id: string;
  type: string;
  required: boolean;
  options: { value: string; label: string }[];
}

export interface SessionView {
  session_id: string;
  lang: Lang;
  stage: "pick_form" | "filling" | "review" | "complete";
  history: ChatMessage[];
  reply: string;
  form: { id: string; title: string; department: string; output: string; category: string } | null;
  progress?: { done: number; total: number };
  fields?: FieldView[];
  current_field?: string | null;
  current?: CurrentQuestion | null;
  computed?: { label: string; value: string }[];
  warnings?: string[];
  documents?: string[];
  submit_note?: string;
  sources?: string[];
  can_download?: boolean;
}
