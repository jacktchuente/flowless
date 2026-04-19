import {NgModule} from '@angular/core';
import {CommonModule} from '@angular/common';
import {TranslateLoader, TranslateModule} from "@ngx-translate/core";
import {HttpClient, provideHttpClient, withInterceptorsFromDi} from "@angular/common/http";
import {TranslateHttpLoader} from "@ngx-translate/http-loader";
import {BrowserAnimationsModule} from "@angular/platform-browser/animations";
import {BrowserModule} from "@angular/platform-browser";
import {ReactiveFormsModule} from "@angular/forms";
import {NgxRequestModule} from "@kwyxyz/ngx-request";
import {NgxAuthModule} from "@kwyxyz/ngx-auth";
import {environment} from "../environments/environment";
import {NotificationService} from "@project-shared/services/notification.service";
import {ConfirmationService, LoadingService, NgxCommonModule} from "@kwyxyz/ngx-common";
import {RoutingPart} from "./_utils/const";
import {CustomFormlyModule} from './custom-formly.module';


@NgModule({
  declarations: [],
  exports: [
    TranslateModule,
    BrowserModule,
    BrowserAnimationsModule,
    ReactiveFormsModule,
    NgxCommonModule,
    NgxRequestModule,
    NgxAuthModule,
  ],
  imports: [CommonModule,
    BrowserModule,
    BrowserAnimationsModule,
    TranslateModule.forRoot({
      loader: {
        provide: TranslateLoader,
        useFactory: httpTranslateLoader,
        deps: [HttpClient],
      }
    }),
    NgxCommonModule.forRoot({
      allowMetaInPage: true
    }),
    NgxRequestModule.forRoot({
      defaultApiUrl: environment.baseUrl,
      confirmationService: ConfirmationService,
      notificationService: NotificationService,
      loadingService: LoadingService,
      defaultWsUrl: environment.wsBaseUrl,
      defaultPublicWs: 'public',
      userSocketUrl: 'user-socket/me',
      dateFields: ["recorded_at", "started_at", "ended_at"]
    }),
    NgxAuthModule.forRoot({
      confirmationService: ConfirmationService,
      notificationService: NotificationService,
      allowedUrls: [environment.baseUrl],
      authApiUrl: environment.authApiUrl,
      allowedOauthProvider: [],
      loginPageUri: RoutingPart.login,
      afterLoginPageUri: `/${RoutingPart.app}`,
      afterLogoutPageUri: `/${RoutingPart.login}`,
      afterRegistrationPageUri: `/${RoutingPart.login}`,
      afterPasswordResetPageUri: `/${RoutingPart.login}`
    }),
    ReactiveFormsModule,
    CustomFormlyModule
  ], providers: [
    provideHttpClient(withInterceptorsFromDi()),

  ]
})
export class InitialModule {
}

export function httpTranslateLoader(http: HttpClient) {
  return new TranslateHttpLoader(http);
}
