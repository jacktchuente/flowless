import { Injectable } from "@angular/core";

export type UiLanguage = "en" | "fr";
export const UI_LANGUAGES: UiLanguage[] = ["en", "fr"];
export const LANGUAGE_STORAGE_KEY = "flowless.settings.language";

export function readStoredLanguage(): UiLanguage | null {
  try {
    const stored = localStorage.getItem(LANGUAGE_STORAGE_KEY);
    return stored === "en" || stored === "fr" ? stored : null;
  } catch {
    return null;
  }
}

@Injectable({ providedIn: "root" })
export class AppSettingsService {
  getLanguage(): UiLanguage {
    return readStoredLanguage() ?? this.detectBrowserLanguage();
  }

  setLanguage(language: UiLanguage): void {
    try {
      localStorage.setItem(LANGUAGE_STORAGE_KEY, language);
    } catch {
      // storage unavailable: language still applies for the session
    }
  }

  private detectBrowserLanguage(): UiLanguage {
    return navigator.languages?.some((v) => v.toLowerCase().startsWith("fr"))
      ? "fr"
      : "en";
  }
}
