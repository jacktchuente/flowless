import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterOutlet } from "@angular/router";
import {BasePageDirective} from "@kwyxyz/ngx-common";


@Component({
  selector: 'app-maintenance',
  standalone: true,
  imports: [CommonModule, RouterOutlet],
  templateUrl: './maintenance.component.html',
  styleUrls: ['./maintenance.component.css']
})
export class MaintenanceComponent extends BasePageDirective {

  pageName = "Maintenance"

  override title = "MaintenanceTitle"
  override description = "MaintenanceDescription"
  override keywords = "MaintenanceKeywords"
  // replace-me 12345

}

