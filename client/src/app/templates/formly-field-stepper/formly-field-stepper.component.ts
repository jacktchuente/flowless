import {Component} from '@angular/core';
import {FieldType, FormlyFieldConfig, FormlyModule} from '@ngx-formly/core';
import {MatStep, MatStepLabel, MatStepper, MatStepperNext, MatStepperPrevious} from "@angular/material/stepper";
import {NgForOf, NgIf} from "@angular/common";

@Component({
  selector: 'app-formly-field-stepper',
  standalone: true,
  imports: [
    MatStepper,
    MatStep,
    FormlyModule,
    MatStepLabel,
    MatStepperPrevious,
    MatStepperNext,
    NgIf,
    NgForOf
  ],
  templateUrl: './formly-field-stepper.component.html',
  styleUrl: './formly-field-stepper.component.css'
})
export class FormlyFieldStepperComponent extends FieldType {
  isValid(field: FormlyFieldConfig): boolean {
    if (field.key) {
      return field.formControl ? field.formControl.valid : false;
    }

    return field.fieldGroup ? field.fieldGroup.every((f) => this.isValid(f)) : true;
  }
}
