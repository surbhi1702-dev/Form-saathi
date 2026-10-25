import { useCallback, useEffect, useRef, useState } from "react";

// Reads text aloud with the device's own voices (Web Speech synthesis).
// Tamil/Hindi/Odia voices depend on the phone or computer: Android with Google
// Text-to-speech usually has Tamil and Hindi; Odia is less common.

/** Make chat text sound natural when spoken. */
export function toSpeech(text: string): string {
  return text
    .replace(/^! /gm, "")
    .replace(/X{2,}[\sX]*/g, "")                       // masked digits: "XXXX XXXX 0124" -> "0124"
    .replace(/\b\d{5,}\b/g, (d) => d.split("").join(" ")) // phone / PIN / account numbers digit by digit
    .replace(/^\s*[-•]\s*/gm, "")
    .replace(/\bRs\. ?/g, "rupees ")
    .replace(/([.!?।:])\s*\n+/g, "$1 ")             // already ends a sentence: just a space
    .replace(/\n{2,}/g, ". ")
    .replace(/\n/g, ", ")
    .replace(/\s+\)/g, ")")
    .replace(/\s{2,}/g, " ")
    .trim();
}

function pickVoice(speechLang: string): SpeechSynthesisVoice | null {
  const voices = window.speechSynthesis?.getVoices() ?? [];
  const base = speechLang.split("-")[0];
  return (
    voices.find((v) => v.lang === speechLang) ??
    voices.find((v) => v.lang.replace("_", "-").startsWith(base + "-")) ??
    voices.find((v) => v.lang.startsWith(base)) ??
    null
  );
}

export function useReadAloud(speechLang: string) {
  const supported = typeof window !== "undefined" && "speechSynthesis" in window;
  const [speaking, setSpeaking] = useState(false);
  const [hasVoice, setHasVoice] = useState(true);
  const onEndRef = useRef<(() => void) | null>(null);

  useEffect(() => {
    if (!supported) return;
    const check = () => setHasVoice(speechLang.startsWith("en") || pickVoice(speechLang) !== null);
    check();
    window.speechSynthesis.addEventListener("voiceschanged", check);
    return () => window.speechSynthesis.removeEventListener("voiceschanged", check);
  }, [speechLang, supported]);

  useEffect(() => () => {
    if (supported) window.speechSynthesis.cancel();
  }, [supported]);

  const stop = useCallback(() => {
    if (!supported) return;
    onEndRef.current = null;
    window.speechSynthesis.cancel();
    setSpeaking(false);
  }, [supported]);

  const speak = useCallback(
    (text: string, onEnd?: () => void) => {
      if (!supported) {
        onEnd?.();
        return;
      }
      window.speechSynthesis.cancel();
      const voice = pickVoice(speechLang);
      // No voice for this language on this device: an English voice would mumble or stay silent.
      // Skip speaking so hands-free mode still moves on to listening.
      if (!voice && !speechLang.startsWith("en")) {
        setHasVoice(false);
        onEnd?.();
        return;
      }
      const u = new SpeechSynthesisUtterance(toSpeech(text));
      u.lang = speechLang;
      if (voice) u.voice = voice;
      u.rate = 0.9; // a little slower than default - easier to follow
      onEndRef.current = onEnd ?? null;
      u.onend = () => {
        setSpeaking(false);
        const cb = onEndRef.current;
        onEndRef.current = null;
        cb?.();
      };
      u.onerror = () => setSpeaking(false);
      setSpeaking(true);
      window.speechSynthesis.speak(u);
    },
    [speechLang, supported],
  );

  return { supported, speaking, hasVoice, speak, stop };
}
