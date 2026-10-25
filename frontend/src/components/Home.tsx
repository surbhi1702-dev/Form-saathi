import { useEffect, useMemo, useRef, useState, type FormEvent } from "react";
import { api, ApiError } from "../api";
import { t } from "../i18n";
import type { FormCard, Lang } from "../types";

const CATEGORY_ORDER = ["bank", "utilities", "property", "tax", "employment", "transport"];

interface Props {
  lang: Lang;
  onOpen: (formId: string) => void;
  onError: (message: string) => void;
}

export function Home({ lang, onOpen, onError }: Props) {
  const [forms, setForms] = useState<FormCard[]>([]);
  const [query, setQuery] = useState("");
  const [matches, setMatches] = useState<FormCard[] | null>(null);
  const [scanning, setScanning] = useState(false);
  const fileInput = useRef<HTMLInputElement>(null);

  useEffect(() => {
    api.forms(lang).then((r) => setForms(r.forms)).catch(() => onError(t("network", lang)));
    setMatches(null);
  }, [lang, onError]);

  const grouped = useMemo(() => {
    const map = new Map<string, FormCard[]>();
    for (const f of forms) map.set(f.category, [...(map.get(f.category) ?? []), f]);
    return CATEGORY_ORDER.filter((c) => map.has(c)).map((c) => [c, map.get(c)!] as const);
  }, [forms]);

  async function search(e: FormEvent) {
    e.preventDefault();
    if (!query.trim()) return;
    try {
      const r = await api.forms(lang, query.trim());
      if (r.forms.length === 1) onOpen(r.forms[0].id);
      else setMatches(r.forms);
    } catch {
      onError(t("network", lang));
    }
  }

  async function scan(file: File) {
    setScanning(true);
    try {
      const card = await api.scan(file);
      onOpen(card.id);
    } catch (err) {
      onError(err instanceof ApiError && err.status ? err.message : t("network", lang));
    } finally {
      setScanning(false);
    }
  }

  return (
    <main className="home">
      <section className="home-intro">
        <h1 className="home-title">{t("whatNeed", lang)}</h1>
        <form className="search" onSubmit={search} role="search">
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder={t("whatNeedPlaceholder", lang)}
            aria-label={t("whatNeed", lang)}
          />
          <button type="submit">{t("findForm", lang)}</button>
        </form>
        {matches && (
          <div className="matches" aria-live="polite">
            {matches.length === 0 ? (
              <p className="muted">{t("noMatch", lang)}</p>
            ) : (
              <FormRows forms={matches} lang={lang} onOpen={onOpen} />
            )}
          </div>
        )}
      </section>

      <section className="catalog" aria-label={t("allForms", lang)}>
        {grouped.map(([category, list]) => (
          <div className="category" key={category}>
            <h2>{t(category, lang)}</h2>
            <FormRows forms={list} lang={lang} onOpen={onOpen} />
          </div>
        ))}
      </section>

      <section className="scan">
        <div>
          <h2>{t("scanTitle", lang)}</h2>
          <p>{t("scanBody", lang)}</p>
        </div>
        <input
          ref={fileInput}
          type="file"
          accept="image/jpeg,image/png,image/webp"
          capture="environment"
          hidden
          onChange={(e) => e.target.files?.[0] && scan(e.target.files[0])}
        />
        <button className="secondary" onClick={() => fileInput.current?.click()} disabled={scanning}>
          {scanning ? t("reading", lang) : t("scanButton", lang)}
        </button>
      </section>

      <p className="privacy">{t("privacy", lang)}</p>
    </main>
  );
}

function FormRows({ forms, lang, onOpen }: { forms: FormCard[]; lang: Lang; onOpen: (id: string) => void }) {
  return (
    <ul className="form-rows">
      {forms.map((f) => (
        <li key={f.id}>
          <button className="form-row" onClick={() => onOpen(f.id)}>
            <span className="form-row-title">{f.title}</span>
            <span className="form-row-desc">{f.description}</span>
            <span className="form-row-meta">{t("questions", lang, { n: f.question_count })}</span>
          </button>
        </li>
      ))}
    </ul>
  );
}
