import type { FormCard, InputMode, Lang, SessionView } from "./types";

const BASE = import.meta.env.VITE_API_BASE ?? "";

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${BASE}${path}`, init);
  } catch {
    throw new ApiError(0, "network");
  }
  if (!res.ok) {
    let detail = res.statusText;
    try {
      detail = (await res.json()).detail ?? detail;
    } catch {
      /* not JSON */
    }
    throw new ApiError(res.status, detail);
  }
  return res.json() as Promise<T>;
}

const json = (body: unknown): RequestInit => ({
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(body),
});

export const api = {
  forms: (lang: Lang, q?: string) =>
    request<{ forms: FormCard[] }>(`/api/forms?lang=${lang}${q ? `&q=${encodeURIComponent(q)}` : ""}`),
  start: (formId: string | null, lang: Lang) => request<SessionView>("/api/sessions", json({ form_id: formId, lang })),
  send: (sid: string, text: string, via: InputMode = "text") =>
    request<SessionView>(`/api/sessions/${sid}/messages`, json({ text, via })),
  language: (sid: string, lang: Lang) => request<SessionView>(`/api/sessions/${sid}/language`, json({ lang })),
  end: (sid: string) => request<{ deleted: boolean }>(`/api/sessions/${sid}`, { method: "DELETE" }),
  pdfUrl: (sid: string, mask: boolean) => `${BASE}/api/sessions/${sid}/pdf${mask ? "?mask=true" : ""}`,
  scan: (file: File) => {
    const body = new FormData();
    body.append("image", file);
    return request<FormCard>("/api/forms/scan", { method: "POST", body });
  },
};
