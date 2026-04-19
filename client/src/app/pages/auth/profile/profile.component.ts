import {Component} from '@angular/core';
import {CommonModule} from '@angular/common';
import {RouterLink, RouterOutlet} from "@angular/router";
import {BasePageDirective} from "@kwyxyz/ngx-common";
import {MatTabLink, MatTabNav, MatTabNavPanel} from "@angular/material/tabs";
import {RoutingPart} from "../../../_utils/const";


@Component({
  selector: 'app-profile',
  standalone: true,
  imports: [CommonModule, RouterOutlet, MatTabNav, MatTabLink, MatTabNavPanel, RouterLink],
  templateUrl: './profile.component.html',
  styleUrls: ['./profile.component.css']
})
export class ProfileComponent extends BasePageDirective {

  pageName = "Profile"

  override title = "ProfileTitle"
  override description = "ProfileDescription"
  override keywords = "ProfileKeywords"
  // replace-me 12345
  links = [
    {view: "Profile", value: ['/', RoutingPart.app, RoutingPart.profile]},
    {view: "Préférence", value: ['/', RoutingPart.app, RoutingPart.userPreference]},
    {view: "Mot de passe", value: ['/', RoutingPart.app, RoutingPart.changePassword]},
    {view: "Api keys", value: ['/', RoutingPart.app, RoutingPart.apiKey]},
  ];
  activeLink: string[] | undefined

}

