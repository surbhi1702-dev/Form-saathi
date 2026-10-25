import { t } from "../i18n";
import type { AccessSettings } from "../settings";
import type { Lang } from "../types";

interface Props {
  lang: Lang;
  settings: AccessSettings;
  onChange: (next: AccessSettings) => void;
  speechSupported: boolean;
  listenSupported: boolean;
}

/** Big, labelled toggles for people with weak eyesight or who can't read comfortably. */
export function AccessBar({ lang, settings, onChange, speechSupported, listenSupported }: Props) {
  const toggle = (key: keyof AccessSettings) => {
    const next = { ...settings, [key]: !settings[key] };
    // hands-free needs read-aloud; turning read-aloud off also ends hands-free
    if (key === "handsFree" && next.handsFree) next.readAloud = true;
    if (key === "readAloud" && !next.readAloud) next.handsFree = false;
    onChange(next);
  };

  const items: { key: keyof AccessSettings; icon: string; label: string; show: boolean }[] = [
    { key: "largeText", icon: "A+", label: t("largeText", lang), show: true },
    { key: "highContrast", icon: "◐", label: t("highContrast", lang), show: true },
    { key: "readAloud", icon: "🔊", label: t("readAloud", lang), show: speechSupported },
    { key: "handsFree", icon: "🎧", label: t("handsFree", lang), show: speechSupported && listenSupported },
  ];

  return (
    <div className="access-bar" role="group" aria-label={t("accessibility", lang)}>
      {items
        .filter((i) => i.show)
        .map((i) => (
          <button
            key={i.key}
            className={`access-toggle ${settings[i.key] ? "on" : ""}`}
            aria-pressed={settings[i.key]}
            onClick={() => toggle(i.key)}
          >
            <span className="access-icon" aria-hidden="true">
              {i.icon}
            </span>
            <span>{i.label}</span>
          </button>
        ))}
    </div>
  );
}
