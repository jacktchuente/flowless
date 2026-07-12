import {
  ApplicationConfig,
  LOCALE_ID,
  importProvidersFrom,
} from "@angular/core";
import { registerLocaleData } from "@angular/common";
import localeFr from "@angular/common/locales/fr";
import { BrowserModule } from "@angular/platform-browser";
import { InitialModule } from "./initial.module";
import { provideAnimationsAsync } from "@angular/platform-browser/animations/async";
import { provideRouter, withComponentInputBinding } from "@angular/router";
import { routes } from "./app.routes";
import { BrowserAnimationsModule } from "@angular/platform-browser/animations";

registerLocaleData(localeFr);

const browserLocale = navigator.languages?.some((v) =>
  v.toLowerCase().startsWith("fr"),
)
  ? "fr"
  : "en-US";

export const appConfig: ApplicationConfig = {
  providers: [
    provideRouter(routes, withComponentInputBinding()),
    importProvidersFrom(BrowserModule, BrowserAnimationsModule, InitialModule),
    provideAnimationsAsync(),
    { provide: LOCALE_ID, useValue: browserLocale },
  ],
};
