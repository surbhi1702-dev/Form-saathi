import { api } from "../api";
import { t } from "../i18n";
import type { Lang, SessionView } from "../types";

interface Props {
  view: SessionView;
  lang: Lang;
  onAnother: () => void;
  onDelete: () => void;
  onGuide: () => void;
}

/** The "paper" side: the official-looking form fills itself in ink as the chat progresses. */
export function PaperForm({ view, lang, onAnother, onDelete, onGuide }: Props) {
  if (!view.form || !view.fields) return null;
  const { done, total } = view.progress ?? { done: 0, total: 0 };
  const complete = view.stage === "complete";

  return (
    <section className={`paper ${complete ? "is-complete" : ""}`} aria-label={t("yourForm", lang)}>
      <header className="paper-head">
        <p className="paper-dept">{view.form.department}</p>
        <h2>{view.form.title}</h2>
        <div className="meter" role="progressbar" aria-valuemin={0} aria-valuemax={total} aria-valuenow={done}>
          <div className="meter-fill" style={{ width: `${total ? (done / total) * 100 : 0}%` }} />
        </div>
        <p className="paper-progress">{t("progress", lang, { done, total })}</p>
      </header>

      {complete && (
        <div className="stamp" aria-label={t("ready", lang)}>
          {t("ready", lang)}
        </div>
      )}

      <ol className="lines">
        {view.fields.map((f) => (
          <li key={f.id} className={`line ${f.status}`} aria-current={f.status === "current" ? "step" : undefined}>
            <span className="line-label">
              {f.label}
              {!f.required && <span className="opt"> ({t("optional", lang)})</span>}
            </span>
            <span className="line-value">
              {f.status === "filled" && <span className="ink">{f.value}</span>}
              {f.status === "skipped" && <span className="skipped-mark">{t("skipped", lang)}</span>}
            </span>
          </li>
        ))}
        {(view.computed ?? []).map((c) => (
          <li key={c.label} className="line filled computed">
            <span className="line-label">{c.label}</span>
            <span className="line-value">
              <span className="ink">{c.value}</span>
            </span>
          </li>
        ))}
      </ol>

      {view.warnings && view.warnings.length > 0 && (
        <div className="note warn">
          <h3>{t("warnings", lang)}</h3>
          <ul>
            {view.warnings.map((w) => (
              <li key={w}>{w}</li>
            ))}
          </ul>
        </div>
      )}

      {view.documents && view.documents.length > 0 && (
        <div className="note">
          <h3>{t("documents", lang)}</h3>
          <ul className="checklist">
            {view.documents.map((d) => (
              <li key={d}>{d}</li>
            ))}
          </ul>
        </div>
      )}

      {view.submit_note && (
        <div className="note">
          <h3>{t("howToSubmit", lang)}</h3>
          <p>{view.submit_note}</p>
        </div>
      )}

      {view.can_download && (
        <div className="actions">
          <div className="guide-cta">
            <button className="primary-link" onClick={onGuide}>
              ✍ {t("guideStart", lang)}
            </button>
            <p className="muted">{t("guideStartHint", lang)}</p>
          </div>
          <a className="secondary-link" href={api.pdfUrl(view.session_id, false)} download>
            {t("download", lang)}
          </a>
          <a className="secondary-link" href={api.pdfUrl(view.session_id, true)} download>
            {t("downloadMasked", lang)}
          </a>
          {complete && (
            <div className="after">
              <button className="text-button" onClick={onAnother}>
                {t("another", lang)}
              </button>
              <button className="text-button danger" onClick={onDelete}>
                {t("finish", lang)}
              </button>
            </div>
          )}
        </div>
      )}
    </section>
  );
}
