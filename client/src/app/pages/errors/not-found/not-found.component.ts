import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterOutlet } from "@angular/router";
import {BasePageDirective} from "@kwyxyz/ngx-common";


@Component({
  selector: 'app-not-found',
  standalone: true,
  imports: [CommonModule, RouterOutlet],
  templateUrl: './not-found.component.html',
  styleUrls: ['./not-found.component.css']
})
export class NotFoundComponent extends BasePageDirective {

  pageName = "NotFound"

  override title = "NotFoundTitle"
  override description = "NotFoundDescription"
  override keywords = "NotFoundKeywords"
  // replace-me 12345

}

