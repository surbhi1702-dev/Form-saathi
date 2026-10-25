import { useCallback, useEffect, useRef, useState } from "react";
import { api, ApiError } from "../api";
import { LANGUAGES, t } from "../i18n";
import type { Box, Guide, GuideStep, Lang } from "../types";
import { useReadAloud } from "../useReadAloud";

interface Props {
  sessionId: string;
  lang: Lang;
  photoUrl?: string; // the photo of the person's own paper form, when they scanned one
  onClose: () => void;
}

/** Walks the person through copying their answers onto the paper form, one box at a time, out loud. */
export function GuidedFill({ sessionId, lang, photoUrl, onClose }: Props) {
  const [guide, setGuide] = useState<Guide | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [idx, setIdx] = useState(0);
  const [size, setSize] = useState<{ w: number; h: number } | null>(null);
  const headingRef = useRef<HTMLHeadingElement>(null);
  const speechLang = LANGUAGES.find((l) => l.code === lang)?.speech ?? "en-IN";
  const voice = useReadAloud(speechLang);

  useEffect(() => {
    api
      .guide(sessionId)
      .then(setGuide)
      .catch((err) => setError(err instanceof ApiError && err.status === 404 ? t("expired", lang) : t("network", lang)));
  }, [sessionId, lang]);

  useEffect(() => {
    if (!photoUrl) return;
    const img = new Image();
    img.onload = () => setSize({ w: img.naturalWidth, h: img.naturalHeight });
    img.src = photoUrl;
  }, [photoUrl]);

  const steps = guide?.steps ?? [];
  const step: GuideStep | undefined = steps[idx];
  const finished = guide !== null && idx >= steps.length;

  const sayStep = useCallback(
    (s: GuideStep) =>
      voice.speak(
        s.value === null
          ? t("guideSayEmpty", lang, { label: s.label })
          : t("guideSay", lang, { label: s.label, value: s.value }),
      ),
    [voice, lang],
  );

  const spell = useCallback(
    (value: string) =>
      voice.speak(
        Array.from(value)
          .map((ch) => (ch === " " ? t("space", lang) : ch))
          .join(", "),
      ),
    [voice, lang],
  );

  // Read each box out as soon as it is shown.
  useEffect(() => {
    if (!guide) return;
    headingRef.current?.focus({ preventScroll: true });
    if (step) sayStep(step);
    else voice.speak(t("guideDone", lang));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [guide, idx]);

  const go = useCallback(
    (delta: number) => setIdx((i) => Math.min(Math.max(i + delta, 0), steps.length)),
    [steps.length],
  );

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
      else if (e.key === "ArrowRight") go(1);
      else if (e.key === "ArrowLeft") go(-1);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [go, onClose]);

  const close = () => {
    voice.stop();
    onClose();
  };

  return (
    <div className="guide" role="dialog" aria-modal="true" aria-label={t("guideStart", lang)}>
      <header className="guide-bar">
        <span className="guide-title">{guide?.form.title}</span>
        <button className="text-button" onClick={close}>
          {t("guideClose", lang)}
        </button>
      </header>

      {error && (
        <div className="guide-body">
          <p className="banner" role="alert">
            {error}
          </p>
        </div>
      )}

      {step && (
        <div className="guide-body">
          <div className="meter" aria-hidden="true">
            <div className="meter-fill" style={{ width: `${(idx / steps.length) * 100}%` }} />
          </div>
          <p className="guide-count">{t("guideStep", lang, { n: idx + 1, total: steps.length })}</p>
          <h2 className="guide-label" ref={headingRef} tabIndex={-1}>
            {step.label}
          </h2>
          {step.printed_label !== step.label && (
            <p className="guide-printed">
              {t("guideOnPaper", lang)}: <strong lang="en">{step.printed_label}</strong>
            </p>
          )}

          {photoUrl && size && step.box ? (
            <PhotoFocus url={photoUrl} size={size} box={step.box} lang={lang} />
          ) : (
            <p className="guide-find">{t("guideNoPhoto", lang)}</p>
          )}

          {step.value === null ? (
            <p className="guide-empty">{t("guideEmpty", lang)}</p>
          ) : (
            <div className="guide-answer">
              <p className="guide-write">{t("guideWrite", lang)}:</p>
              <p className="tiles" lang="en" aria-label={step.value}>
                {step.value.split(" ").map((word, w) => (
                  // a word's letters stay together on one line where they fit
                  <span key={w} className="tile-word" aria-hidden="true">
                    {Array.from(word).map((ch, i) => (
                      <span key={i} className="tile">
                        {ch}
                      </span>
                    ))}
                  </span>
                ))}
              </p>
            </div>
          )}

          <div className="guide-voice">
            <button className="secondary" onClick={() => sayStep(step)} disabled={!voice.supported}>
              🔊 {voice.speaking ? t("speaking", lang) : t("guideAgain", lang)}
            </button>
            {step.value !== null && (
              <button className="secondary" onClick={() => spell(step.value!)} disabled={!voice.supported}>
                {t("guideSpell", lang)}
              </button>
            )}
          </div>
          {!voice.hasVoice && <p className="muted guide-novoice">{t("noVoice", lang)}</p>}
        </div>
      )}

      {finished && (
        <div className="guide-body guide-finished">
          <div className="stamp">{t("ready", lang)}</div>
          <h2 ref={headingRef} tabIndex={-1}>
            {t("guideDone", lang)}
          </h2>
        </div>
      )}

      {guide && (
        <footer className="guide-nav">
          <button className="secondary" onClick={() => go(-1)} disabled={idx === 0}>
            ← {t("guideBack", lang)}
          </button>
          {finished ? (
            <button className="primary" onClick={close}>
              {t("guideClose", lang)}
            </button>
          ) : (
            <button className="primary" onClick={() => go(1)}>
              {idx === steps.length - 1 ? t("guideFinish", lang) : `${t("guideNext", lang)} →`}
            </button>
          )}
        </footer>
      )}
    </div>
  );
}

/** The photo zoomed in on one box, with the box outlined, plus a small whole-page view to find it. */
function PhotoFocus({ url, size, box, lang }: { url: string; size: { w: number; h: number }; box: Box; lang: Lang }) {
  const crop = cropAround(box, size.w / size.h);
  const pct = (v: number) => `${v * 100}%`;
  const aspect = (crop.w * size.w) / (crop.h * size.h);
  const ring = {
    left: pct((box.x - crop.x) / crop.w),
    top: pct((box.y - crop.y) / crop.h),
    width: pct(box.w / crop.w),
    height: pct(box.h / crop.h),
  };
  return (
    <div className="focus">
      {/* sized by width so the window keeps the crop's exact shape (the box outline depends on it) */}
      <div className="focus-zoom" style={{ aspectRatio: String(aspect), width: `min(100%, calc(46vh * ${aspect}))` }}>
        <img
          src={url}
          alt=""
          style={{ width: pct(1 / crop.w), left: pct(-crop.x / crop.w), top: pct(-crop.y / crop.h) }}
        />
        <span className="focus-ring" style={ring} />
      </div>
      <figure className="focus-page">
        <div className="focus-page-img">
          <img src={url} alt="" />
          <span
            className="focus-ring small"
            style={{ left: pct(box.x), top: pct(box.y), width: pct(box.w), height: pct(box.h) }}
          />
        </div>
        <figcaption>{t("guideWholePage", lang)}</figcaption>
      </figure>
    </div>
  );
}

/** A window around the box (fractions of the photo), wide enough to show the printed label next to it. */
export function cropAround(box: Box, aspect: number): Box {
  const w = Math.min(1, Math.max(box.w * 1.5, 0.5));
  // aim for a 16:9 window, but always tall enough to show the whole box with some room around it
  const h = Math.min(1, Math.max((w * aspect * 9) / 16, box.h * 2.2));
  const clamp = (v: number, size: number) => Math.min(Math.max(v, 0), 1 - size);
  return { x: clamp(box.x + box.w / 2 - w / 2, w), y: clamp(box.y + box.h / 2 - h / 2, h), w, h };
}
