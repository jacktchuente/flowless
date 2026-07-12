import { NgModule } from "@angular/core";
import { CommonModule } from "@angular/common";
import { TranslateLoader, TranslateModule } from "@ngx-translate/core";
import {
  HttpClient,
  provideHttpClient,
  withInterceptorsFromDi,
} from "@angular/common/http";
import { TranslateHttpLoader } from "@ngx-translate/http-loader";
import { BrowserAnimationsModule } from "@angular/platform-browser/animations";
import { BrowserModule } from "@angular/platform-browser";
import { ReactiveFormsModule } from "@angular/forms";
import { NgxRequestModule } from "@kwyxyz/ngx-request";
import { environment } from "../environments/environment";
import { NotificationService } from "@project-shared/services/notification.service";
import { FlwConfirmationService } from "./ui/confirmation.service";
import { FlwLoadingService } from "./ui/loading.service";

@NgModule({
  declarations: [],
  exports: [
    TranslateModule,
    BrowserModule,
    BrowserAnimationsModule,
    ReactiveFormsModule,
    NgxRequestModule,
  ],
  imports: [
    CommonModule,
    BrowserModule,
    BrowserAnimationsModule,
    TranslateModule.forRoot({
      loader: {
        provide: TranslateLoader,
        useFactory: httpTranslateLoader,
        deps: [HttpClient],
      },
    }),
    NgxRequestModule.forRoot({
      defaultApiUrl: environment.baseUrl,
      notificationService: NotificationService,
      confirmationService: FlwConfirmationService,
      loadingService: FlwLoadingService,
      defaultWsUrl: environment.wsBaseUrl,
      defaultPublicWs: "public",
      userSocketUrl: "user-socket/me",
      dateFields: ["recorded_at", "started_at", "ended_at"],
    }),
    ReactiveFormsModule,
  ],
  providers: [provideHttpClient(withInterceptorsFromDi())],
})
export class InitialModule {}

export function httpTranslateLoader(http: HttpClient) {
  return new TranslateHttpLoader(http);
}
