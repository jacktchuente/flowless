import {Component} from '@angular/core';
import {NgFor} from "@angular/common";
import {RouterLink, RouterLinkActive, RouterOutlet} from "@angular/router";
import {environment} from "../../../environments/environment";
import {TranslateModule} from "@ngx-translate/core";

@Component({
  selector: 'app-base',
  standalone: true,
  imports: [
    NgFor,
    RouterLink,
    RouterLinkActive,
    RouterOutlet,
    TranslateModule,
  ],
  templateUrl: './base.component.html',
  styleUrl: './base.component.css'
})
export class BaseComponent {
  readonly menuItems = [
    {label: 'NAV.SOURCES', route: 'sources'},
    {label: 'NAV.COLLECTIONS', route: 'collections'},
    {label: 'NAV.MEDIAS', route: 'medias'},
    {label: 'NAV.CHANNELS', route: 'channels'},
  ]
  readonly adminUrl = '/admin/'
  protected appName = environment.appName;
}
