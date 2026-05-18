import {ApplicationConfig, importProvidersFrom} from '@angular/core';
import {BrowserModule} from '@angular/platform-browser';
import {InitialModule} from "./initial.module";
import {provideAnimationsAsync} from "@angular/platform-browser/animations/async";
import {provideRouter, withComponentInputBinding} from "@angular/router";
import {routes} from "./app.routes";
import {DatePipe} from "@angular/common";
import {BrowserAnimationsModule} from "@angular/platform-browser/animations";
import {providePrimeNG} from "primeng/config";
import Aura from '@primeng/themes/aura';
import {CalendarModule, DateAdapter} from "angular-calendar";
import {adapterFactory} from "angular-calendar/date-adapters/date-fns";

export const appConfig: ApplicationConfig = {
  providers: [
    provideRouter(routes, withComponentInputBinding()),
    importProvidersFrom(
      BrowserModule,
      BrowserAnimationsModule,
      InitialModule,
      CalendarModule.forRoot({
        provide: DateAdapter,
        useFactory: adapterFactory,
      }),
    ),
    provideAnimationsAsync(),
    providePrimeNG({
      theme: {
        preset: Aura
      }
    })
  ]
};
