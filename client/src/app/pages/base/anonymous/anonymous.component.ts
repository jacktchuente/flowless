import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterOutlet } from "@angular/router";
import {BasePageDirective} from "@kwyxyz/ngx-common";


@Component({
  selector: 'app-anonymous',
  standalone: true,
  imports: [CommonModule, RouterOutlet],
  templateUrl: './anonymous.component.html',
  styleUrls: ['./anonymous.component.css']
})
export class AnonymousComponent extends BasePageDirective {

  pageName = "Anonymous"

  override title = "AnonymousTitle"
  override description = "AnonymousDescription"
  override keywords = "AnonymousKeywords"
  // replace-me 12345

}

