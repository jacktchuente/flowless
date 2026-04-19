import {Component, EventEmitter, Output} from '@angular/core';
import {FieldType} from "@ngx-formly/core";
import {MatButton, MatIconButton} from "@angular/material/button";
import {MatIcon} from "@angular/material/icon";

@Component({
  selector: 'app-button-input1',
  standalone: true,
  imports: [
    MatButton,
    MatIconButton,
    MatIcon
  ],
  templateUrl: './button-input1.component.html',
  styleUrl: './button-input1.component.css'
})
export class ButtonInput1Component extends FieldType {

  onClick() {
    this.props['onClick']()
  }
}
