import {Component} from '@angular/core';
import {FieldArrayType, FormlyModule} from "@ngx-formly/core";
import {NgForOf, NgIf} from "@angular/common";

@Component({
  selector: 'app-repeat-type',
  imports: [
    FormlyModule,
    NgIf,
    NgForOf
  ],
  standalone: true,
  templateUrl: './repeat-type.component.html',
  styleUrl: './repeat-type.component.css'
})
export class RepeatTypeComponent extends FieldArrayType {
}
