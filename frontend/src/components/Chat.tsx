import { useCallback, useEffect, useRef, useState } from "react";
import { LANGUAGES, t } from "../i18n";
import type { AccessSettings } from "../settings";
import type { InputMode, Lang, SessionView } from "../types";
import { useReadAloud } from "../useReadAloud";
import { useSpeech } from "../useSpeech";

interface Props {
  view: SessionView;
  lang: Lang;
  busy: boolean;
  settings: AccessSettings;
  onSend: (text: string, via: InputMode) => void;
}

export function Chat({ view, lang, busy, settings, onSend }: Props) {
  const [text, setText] = useState("");
  const [silentTries, setSilentTries] = useState(0);
  const endRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const lastSpoken = useRef<number>(-1);
  const triesRef = useRef(0);
  const speechLang = LANGUAGES.find((l) => l.code === lang)?.speech ?? "en-IN";
  const voice = useReadAloud(speechLang);

  const submit = useCallback(
    (value: string, via: InputMode = "text") => {
      const v = value.trim();
      if (!v || busy) return;
      voice.stop();
      triesRef.current = 0;
      setSilentTries(0);
      onSend(v, via);
      setText("");
    },
    [busy, onSend, voice],
  );

  // Hands-free: if nothing was heard, ask once more, then wait for a tap.
  const startListeningRef = useRef<() => void>(() => undefined);
  const onSilent = useCallback(() => {
    if (!settings.handsFree) return;
    triesRef.current += 1;
    setSilentTries(triesRef.current);
    if (triesRef.current <= 1) voice.speak(t("didNotHear", lang), () => startListeningRef.current());
  }, [settings.handsFree, lang, voice]);

  const onHeard = useCallback((heard: string) => submit(heard, "voice"), [submit]);
  const speech = useSpeech(speechLang, onHeard, onSilent);
  startListeningRef.current = speech.start;
  const finished = view.stage === "complete";

  // Read each new assistant message aloud; in hands-free mode, listen straight after.
  useEffect(() => {
    const idx = view.history.length - 1;
    const last = view.history[idx];
    if (!last || last.role !== "assistant" || busy || idx === lastSpoken.current) return;
    lastSpoken.current = idx;
    if (!settings.readAloud && !settings.handsFree) return;
    voice.speak(last.text, settings.handsFree && !finished ? () => speech.start() : undefined);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [view.history, busy, settings.readAloud, settings.handsFree, finished]);

  // Turning hands-free off stops everything immediately.
  useEffect(() => {
    if (!settings.handsFree) speech.stop();
    if (!settings.readAloud && !settings.handsFree) voice.stop();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [settings.handsFree, settings.readAloud]);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [view.history.length, busy]);

  useEffect(() => {
    if (!busy && !settings.handsFree) inputRef.current?.focus({ preventScroll: true });
  }, [busy, settings.handsFree]);

  const current = view.current;
  const quick: { label: string; send: string; kind?: string }[] = [];
  if (view.stage === "filling" && current) {
    for (const o of current.options) quick.push({ label: o.label, send: o.value });
    quick.push({ label: t("explain", lang), send: t("explain", lang), kind: "ghost" });
    if (!current.required) quick.push({ label: t("skip", lang), send: "skip", kind: "ghost" });
  }
  if (view.stage === "review") quick.push({ label: t("yes", lang), send: "yes" });

  const status = speech.listening ? t("listening", lang) : voice.speaking ? t("speaking", lang) : null;
  const showNoVoice = (settings.readAloud || settings.handsFree) && voice.supported && !voice.hasVoice;

  return (
    <section className="chat" aria-label="Conversation">
      <div className="messages" role="log" aria-live="polite">
        {view.history.map((m, i) => (
          <div key={i} className={`msg ${m.role}`}>
            <p>{m.text}</p>
            {m.role === "assistant" && voice.supported && (
              <button className="speak-again" onClick={() => voice.speak(m.text)} aria-label={t("listenAgain", lang)}>
                🔊 {t("listenAgain", lang)}
              </button>
            )}
            {m.sources && m.sources.length > 0 && (
              <details className="sources">
                <summary>{t("sources", lang)}</summary>
                <ul>
                  {m.sources.map((s) => (
                    <li key={s}>{s}</li>
                  ))}
                </ul>
              </details>
            )}
          </div>
        ))}
        {busy && (
          <div className="msg assistant typing" aria-label="…">
            <span />
            <span />
            <span />
          </div>
        )}
        <div ref={endRef} />
      </div>

      {showNoVoice && <p className="voice-hint">{t("noVoice", lang)}</p>}

      {status && (
        <div className={`voice-status ${speech.listening ? "listening" : ""}`} role="status">
          <span className="pulse" aria-hidden="true" />
          {status}
          <button
            className="text-button"
            onClick={() => {
              speech.stop();
              voice.stop();
            }}
          >
            {t("stop", lang)}
          </button>
        </div>
      )}

      {quick.length > 0 && (
        <div className="quick">
          {quick.map((q) => (
            <button key={q.label} className={`chip ${q.kind ?? ""}`} onClick={() => submit(q.send, "tap")} disabled={busy}>
              {q.label}
            </button>
          ))}
        </div>
      )}

      {!finished && (
        <form
          className="composer"
          onSubmit={(e) => {
            e.preventDefault();
            submit(text);
          }}
        >
          <textarea
            ref={inputRef}
            rows={1}
            value={text}
            maxLength={1000}
            placeholder={t("typeAnswer", lang)}
            aria-label={t("typeAnswer", lang)}
            onChange={(e) => setText(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                submit(text);
              }
            }}
          />
          {speech.supported && (
            <button
              type="button"
              className={`mic ${speech.listening ? "on" : ""} ${settings.handsFree ? "big" : ""}`}
              onClick={() => {
                voice.stop();
                speech.toggle();
              }}
              aria-label={speech.listening ? t("listening", lang) : t("speak", lang)}
              title={speech.listening ? t("listening", lang) : t("speak", lang)}
            >
              <svg viewBox="0 0 24 24" aria-hidden="true">
                <path d="M12 15a3 3 0 0 0 3-3V6a3 3 0 1 0-6 0v6a3 3 0 0 0 3 3Zm5-3a5 5 0 0 1-10 0H5a7 7 0 0 0 6 6.92V21h2v-2.08A7 7 0 0 0 19 12h-2Z" />
              </svg>
            </button>
          )}
          <button type="submit" className="send" disabled={busy || !text.trim()}>
            {t("send", lang)}
          </button>
        </form>
      )}
      {silentTries > 1 && settings.handsFree && <p className="voice-hint">{t("tapMic", lang)}</p>}
    </section>
  );
}
