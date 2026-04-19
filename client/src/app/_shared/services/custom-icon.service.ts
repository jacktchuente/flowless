import {DomSanitizer} from '@angular/platform-browser';
import {MatIconRegistry} from '@angular/material/icon';
import {Injectable} from '@angular/core';


@Injectable({
  providedIn: 'root'
})
export class CustomIconService {

  customIcons: { [indexer: string]: string } = {
    facebook: "assets/icons/facebook.svg",
    microsoft: "assets/icons/microsoft.svg",
    twitter: "assets/icons/twitter.svg",
    linkedin: "assets/icons/linkedin.svg",
    google: "assets/icons/google.svg",
    discord: "assets/icons/discord.svg",
  };

  constructor(
    private matIconRegistry: MatIconRegistry,
    private domSanitizer: DomSanitizer
  ) {
    this.init()
  }

  init(): void {
    for (const key of Object.keys(this.customIcons)) {
      this.matIconRegistry.addSvgIcon(
        key,
        this.domSanitizer.bypassSecurityTrustResourceUrl(this.customIcons[key])
      );
    }
  }
}

export enum CustomIcons {
  facebook = "facebook",
  microsoft = "microsoft",
  twitter = "twitter",
  linkedin = "linkedin",
  google = "google",
  discord = "discord",
}
