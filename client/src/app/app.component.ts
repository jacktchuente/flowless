import { Component } from "@angular/core";
import { NgIf } from "@angular/common";
import { RouterOutlet } from "@angular/router";
import { TranslateService } from "@ngx-translate/core";
import { WebsocketService } from "@kwyxyz/ngx-request";
import { AppSettingsService } from "@project-services/app-settings.service";
import { environment } from "../environments/environment";
@Component({
  selector: "app-root",
  standalone: true,
  imports: [RouterOutlet, NgIf],
  templateUrl: "./app.component.html",
  styleUrl: "./app.component.css",
})
export class AppComponent {
  title = "my_awesome_client";
  showAlert = environment.mode === "demo";
  constructor(
    websocket: WebsocketService,
    translate: TranslateService,
    settings: AppSettingsService,
  ) {
    translate.setDefaultLang("fr");
    translate.use(settings.getLanguage());
    websocket.initSockets();
  }
}
