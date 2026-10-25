export interface AccessSettings {
  largeText: boolean;
  highContrast: boolean;
  readAloud: boolean;
  handsFree: boolean;
}

const KEY = "formsaathi.access";
export const DEFAULT_SETTINGS: AccessSettings = { largeText: false, highContrast: false, readAloud: false, handsFree: false };

export function loadSettings(): AccessSettings {
  try {
    return { ...DEFAULT_SETTINGS, ...JSON.parse(localStorage.getItem(KEY) ?? "{}") };
  } catch {
    return DEFAULT_SETTINGS;
  }
}

export function saveSettings(s: AccessSettings) {
  try {
    localStorage.setItem(KEY, JSON.stringify(s));
  } catch {
    /* storage unavailable - settings last for this visit only */
  }
}

export function applySettings(s: AccessSettings) {
  const root = document.documentElement;
  root.dataset.textsize = s.largeText ? "large" : "normal";
  root.dataset.contrast = s.highContrast ? "high" : "normal";
}
