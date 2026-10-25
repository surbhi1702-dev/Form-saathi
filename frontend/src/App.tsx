import { useCallback, useEffect, useState, type ReactNode } from "react";
import { api, ApiError } from "./api";
import { AccessBar } from "./components/AccessBar";
import { Chat } from "./components/Chat";
import { GuidedFill } from "./components/GuidedFill";
import { Home } from "./components/Home";
import { PaperForm } from "./components/PaperForm";
import { LANGUAGES, t } from "./i18n";
import { applySettings, loadSettings, saveSettings, type AccessSettings } from "./settings";
import type { InputMode, Lang, SessionView } from "./types";
import { speechRecognitionSupported } from "./useSpeech";

const SPEECH_OUT = typeof window !== "undefined" && "speechSynthesis" in window;
const SPEECH_IN = speechRecognitionSupported();

function readLang(): Lang | null {
  try {
    const v = localStorage.getItem("formsaathi.lang");
    return v === "en" || v === "ta" || v === "hi" || v === "or" ? v : null;
  } catch {
    return null;
  }
}

function saveLang(lang: Lang) {
  try {
    localStorage.setItem("formsaathi.lang", lang);
  } catch {
    /* storage unavailable - language just won't be remembered */
  }
}

export default function App() {
  const [lang, setLang] = useState<Lang | null>(readLang);
  const [view, setView] = useState<SessionView | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [sheetOpen, setSheetOpen] = useState(false);
  const [settings, setSettings] = useState<AccessSettings>(loadSettings);
  const [guiding, setGuiding] = useState(false);
  // Photos of scanned paper forms, by form id. Kept only in this browser tab, never stored on the server.
  const [photos, setPhotos] = useState<Record<string, string>>({});

  useEffect(() => {
    applySettings(settings);
    saveSettings(settings);
  }, [settings]);

  useEffect(() => {
    document.documentElement.lang = lang ?? "en";
  }, [lang]);

  const showError = useCallback((message: string) => setError(message), []);

  const handleFailure = useCallback(
    (err: unknown, current: Lang) => {
      if (err instanceof ApiError && err.status === 404) {
        setView(null);
        setError(t("expired", current));
      } else {
        setError(err instanceof ApiError && err.status ? err.message : t("network", current));
      }
    },
    [],
  );

  const chooseLang = async (next: Lang) => {
    setLang(next);
    saveLang(next);
    if (view) {
      setBusy(true);
      try {
        setView(await api.language(view.session_id, next));
      } catch (err) {
        handleFailure(err, next);
      } finally {
        setBusy(false);
      }
    }
  };

  const open = async (formId: string, photoUrl?: string) => {
    if (!lang) return;
    if (photoUrl) setPhotos((p) => ({ ...p, [formId]: photoUrl }));
    setError(null);
    setBusy(true);
    try {
      setView(await api.start(formId, lang));
      setSheetOpen(false);
    } catch (err) {
      handleFailure(err, lang);
    } finally {
      setBusy(false);
    }
  };

  const send = useCallback(
    async (text: string, via: InputMode = "text") => {
      if (!view || !lang) return;
      setError(null);
      // optimistic: show the user's message straight away
      setView({ ...view, history: [...view.history, { role: "user", text }] });
      setBusy(true);
      try {
        setView(await api.send(view.session_id, text, via));
      } catch (err) {
        handleFailure(err, lang);
      } finally {
        setBusy(false);
      }
    },
    [view, lang, handleFailure],
  );

  const goHome = () => {
    setView(null);
    setGuiding(false);
    setError(null);
  };

  const deleteData = async () => {
    if (view) await api.end(view.session_id).catch(() => undefined);
    goHome();
  };

  if (!lang)
    return (
      <LanguageGate
        onPick={chooseLang}
        bar={
          <AccessBar
            lang="en"
            settings={settings}
            onChange={setSettings}
            speechSupported={SPEECH_OUT}
            listenSupported={SPEECH_IN}
          />
        }
      />
    );

  return (
    <div className="app">
      <header className="topbar">
        <button className="brand" onClick={goHome} aria-label="Form Saathi home">
          <span className="brand-mark" aria-hidden="true">
            ✍
          </span>
          <span className="brand-name">Form Saathi</span>
        </button>
        <AccessBar
          lang={lang}
          settings={settings}
          onChange={setSettings}
          speechSupported={SPEECH_OUT}
          listenSupported={SPEECH_IN}
        />
        <div className="lang-switch" role="group" aria-label={t("chooseLanguage", lang)}>
          {LANGUAGES.map((l) => (
            <button
              key={l.code}
              className={l.code === lang ? "active" : ""}
              aria-pressed={l.code === lang}
              lang={l.code}
              onClick={() => chooseLang(l.code)}
              disabled={busy}
            >
              {l.name}
            </button>
          ))}
        </div>
      </header>

      {error && (
        <div className="banner" role="alert">
          <span>{error}</span>
          <button className="text-button" onClick={() => setError(null)} aria-label="Dismiss">
            ×
          </button>
        </div>
      )}

      {!view ? (
        <Home lang={lang} onOpen={open} onError={showError} />
      ) : (
        <div className="workspace-wrap">
          <div className="workspace-title">
            <button className="text-button" onClick={goHome}>
              ← {t("allForms", lang)}
            </button>
            <button className="text-button sheet-toggle" onClick={() => setSheetOpen((s) => !s)}>
              {sheetOpen ? t("hideForm", lang) : `${t("showForm", lang)} (${view.progress?.done ?? 0}/${view.progress?.total ?? 0})`}
            </button>
          </div>
          <div className={`workspace ${sheetOpen ? "sheet-open" : ""}`}>
            <div className="workspace-chat">
              <Chat view={view} lang={lang} busy={busy} settings={settings} onSend={send} />
            </div>
            <div className="workspace-paper">
              <PaperForm
                view={view}
                lang={lang}
                onAnother={goHome}
                onDelete={deleteData}
                onGuide={() => setGuiding(true)}
              />
            </div>
          </div>
        </div>
      )}

      {view && guiding && (
        <GuidedFill
          sessionId={view.session_id}
          lang={lang}
          photoUrl={view.form ? photos[view.form.id] : undefined}
          onClose={() => setGuiding(false)}
        />
      )}
    </div>
  );
}

function LanguageGate({ onPick, bar }: { onPick: (l: Lang) => void; bar: ReactNode }) {
  return (
    <main className="gate">
      <div className="gate-inner">
        <div className="gate-access">{bar}</div>
        <p className="gate-brand">
          <span className="brand-mark" aria-hidden="true">
            ✍
          </span>{" "}
          Form Saathi
        </p>
        <h1>
          {LANGUAGES.map((l) => (
            <span key={l.code} lang={l.code} className="gate-line">
              {t("chooseLanguage", l.code)}
            </span>
          ))}
        </h1>
        <div className="gate-options">
          {LANGUAGES.map((l) => (
            <button key={l.code} lang={l.code} onClick={() => onPick(l.code)}>
              <span className="gate-name">{l.name}</span>
              <span className="gate-tag">{t("tagline", l.code)}</span>
            </button>
          ))}
        </div>
      </div>
    </main>
  );
}
