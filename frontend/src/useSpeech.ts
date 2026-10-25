import { useCallback, useEffect, useRef, useState } from "react";

// Browser speech recognition (Chrome / Edge / Android). Not in every browser,
// so the mic button and hands-free mode are hidden when it isn't available.
type Recognition = {
  lang: string;
  interimResults: boolean;
  continuous: boolean;
  onresult: ((e: { results: ArrayLike<ArrayLike<{ transcript: string }>> }) => void) | null;
  onend: (() => void) | null;
  onerror: (() => void) | null;
  start: () => void;
  stop: () => void;
};

function getCtor(): (new () => Recognition) | null {
  const w = window as unknown as Record<string, unknown>;
  return (w.SpeechRecognition ?? w.webkitSpeechRecognition ?? null) as (new () => Recognition) | null;
}

export function speechRecognitionSupported(): boolean {
  return typeof window !== "undefined" && getCtor() !== null;
}

/**
 * onText   - called with what the person said
 * onSilent - called when listening ended without hearing anything (hands-free uses it)
 */
export function useSpeech(speechLang: string, onText: (text: string) => void, onSilent?: () => void) {
  const [listening, setListening] = useState(false);
  const rec = useRef<Recognition | null>(null);
  const supported = speechRecognitionSupported();
  const handlers = useRef({ onText, onSilent });
  handlers.current = { onText, onSilent };

  useEffect(() => () => rec.current?.stop(), []);

  const start = useCallback(() => {
    const Ctor = getCtor();
    if (!Ctor) return;
    rec.current?.stop();
    const r = new Ctor();
    let heard = false;
    r.lang = speechLang;
    r.interimResults = false;
    r.continuous = false;
    r.onresult = (e) => {
      const text = Array.from(e.results)
        .map((res) => res[0].transcript)
        .join(" ")
        .trim();
      if (text) {
        heard = true;
        handlers.current.onText(text);
      }
    };
    r.onend = () => {
      setListening(false);
      if (!heard) handlers.current.onSilent?.();
    };
    r.onerror = () => setListening(false);
    rec.current = r;
    setListening(true);
    try {
      r.start();
    } catch {
      setListening(false);
    }
  }, [speechLang]);

  const stop = useCallback(() => {
    rec.current?.stop();
    setListening(false);
  }, []);

  const toggle = useCallback(() => (listening ? stop() : start()), [listening, start, stop]);

  return { supported, listening, start, stop, toggle };
}
