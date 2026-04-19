import {Component} from '@angular/core';
import {CustomIconService} from "@project-shared/services/custom-icon.service";
import {AuthService} from "@kwyxyz/ngx-auth";
import {WebsocketService} from "@kwyxyz/ngx-request";
import {PreferenceService} from "@kwyxyz/ngx-common";
import {RouterOutlet} from '@angular/router';
import {UserPreferenceService} from "@project-services/user-preference.service";
import {TranslateService} from "@ngx-translate/core";
import {MtxAlert} from "@ng-matero/extensions/alert";
import {NgIf} from "@angular/common";
import {environment} from "../environments/environment";

@Component({
  selector: 'app-root',
  templateUrl: './app.component.html',
  styleUrls: ['./app.component.css'],
  standalone: true,
  imports: [RouterOutlet, MtxAlert, NgIf]
})
export class AppComponent {
  title = 'my_awesome_client';
  showAlert = environment.mode === "demo";

  constructor(
    private authService: AuthService,
    private webSocketService: WebsocketService,
    private userPreferenceService: UserPreferenceService,
    private customIconService: CustomIconService,
    private languageService: PreferenceService,
    private translateService: TranslateService
  ) {
    this.languageService.initLanguage(["en", "fr"], "fr")
    this.customIconService.init()

    this.authService.isLoggedSubject.subscribe(
      x => {
        if (x) {
          this.webSocketService.initSockets()
        }
      }
    )


  }

}
