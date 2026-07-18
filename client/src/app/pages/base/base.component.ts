import { Component } from "@angular/core";
import { NgFor } from "@angular/common";
import { RouterLink, RouterLinkActive, RouterOutlet } from "@angular/router";
import { TranslateModule } from "@ngx-translate/core";
import { environment } from "../../../environments/environment";
import { FlwIconComponent } from "../../ui/icon/flw-icon.component";
import { FlwToastHostComponent } from "../../ui/toast/flw-toast-host.component";
@Component({
  selector: "app-base",
  standalone: true,
  imports: [
    NgFor,
    RouterLink,
    RouterLinkActive,
    RouterOutlet,
    TranslateModule,
    FlwIconComponent,
    FlwToastHostComponent,
  ],
  templateUrl: "./base.component.html",
  styleUrl: "./base.component.css",
})
export class BaseComponent {
  readonly menuItems = [
    { label: "NAV.OVERVIEW", route: "overview", icon: "dashboard" },
    { label: "NAV.SOURCES", route: "sources", icon: "sources" },
    { label: "NAV.COLLECTIONS", route: "collections", icon: "collections" },
    { label: "NAV.MEDIAS", route: "medias", icon: "medias" },
    { label: "NAV.CHANNELS", route: "channels", icon: "channels" },
    {
      label: "NAV.CHANNEL_IMAGES",
      route: "channel-images",
      icon: "image",
    },
    {
      label: "NAV.EDITORIAL_PLANNING",
      route: "editorial-planning",
      icon: "planning",
    },
    { label: "NAV.SETTINGS", route: "settings", icon: "settings" },
  ];
  readonly adminUrl = "/admin/";
  readonly appName = environment.appName;
}
