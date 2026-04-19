import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterOutlet } from "@angular/router";
import {BasePageDirective} from "@kwyxyz/ngx-common";


@Component({
  selector: 'app-reset-password',
  standalone: true,
  imports: [CommonModule, RouterOutlet],
  templateUrl: './reset-password.component.html',
  styleUrls: ['./reset-password.component.css']
})
export class ResetPasswordComponent extends BasePageDirective {

  pageName = "ResetPassword"

  override title = "ResetPasswordTitle"
  override description = "ResetPasswordDescription"
  override keywords = "ResetPasswordKeywords"
  // replace-me 12345

}

