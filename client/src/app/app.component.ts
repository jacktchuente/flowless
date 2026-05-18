import {Component} from '@angular/core';
import {CustomIconService} from "@project-shared/services/custom-icon.service";
import {WebsocketService} from "@kwyxyz/ngx-request";
import {PreferenceService} from "@kwyxyz/ngx-common";
import {RouterOutlet} from '@angular/router';
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
    private webSocketService: WebsocketService,
    private customIconService: CustomIconService,
    private languageService: PreferenceService,
  ) {
    const defaultLanguage = this.resolveBrowserLanguage()
    this.languageService.initLanguage(["en", "fr"], defaultLanguage)
    this.customIconService.init()
    this.webSocketService.initSockets()
  }

  private resolveBrowserLanguage(): "en" | "fr" {
    const browserLanguages = navigator.languages?.length ? navigator.languages : [navigator.language]
    for (const language of browserLanguages) {
      const normalizedLanguage = language?.toLowerCase().split('-')[0]
      if (normalizedLanguage === 'en') {
        return 'en'
      }
      if (normalizedLanguage === 'en') {
        return 'en'
      }
    }
    return 'en'
  }
}
