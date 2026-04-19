import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterOutlet } from "@angular/router";
import {BasePageDirective} from "@kwyxyz/ngx-common";


@Component({
  selector: 'app-logout',
  standalone: true,
  imports: [CommonModule, RouterOutlet],
  templateUrl: './logout.component.html',
  styleUrls: ['./logout.component.css']
})
export class LogoutComponent extends BasePageDirective {

  pageName = "Logout"

  override title = "LogoutTitle"
  override description = "LogoutDescription"
  override keywords = "LogoutKeywords"
  // replace-me 12345

}

