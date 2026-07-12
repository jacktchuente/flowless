import {
  Component,
  EventEmitter,
  forwardRef,
  Input,
  Output,
} from "@angular/core";
import { NgFor } from "@angular/common";
import { ControlValueAccessor, NG_VALUE_ACCESSOR } from "@angular/forms";
export interface FlwSegmentedOption {
  label: string;
  value: unknown;
}
@Component({
  selector: "flw-segmented",
  standalone: true,
  imports: [NgFor],
  template: `<div class="segmented">
    <button
      type="button"
      *ngFor="let option of options"
      [class.active]="option.value === value"
      [disabled]="disabled"
      (click)="choose(option.value)"
    >
      {{ option.label }}
    </button>
  </div>`,
  providers: [
    {
      provide: NG_VALUE_ACCESSOR,
      useExisting: forwardRef(() => FlwSegmentedComponent),
      multi: true,
    },
  ],
})
export class FlwSegmentedComponent implements ControlValueAccessor {
  @Input() options: FlwSegmentedOption[] = [];
  @Input() value: unknown;
  @Output() valueChange = new EventEmitter<unknown>();
  disabled = false;
  private change = (v: unknown) => {};
  touched = () => {};
  choose(v: unknown) {
    this.value = v;
    this.change(v);
    this.valueChange.emit(v);
    this.touched();
  }
  writeValue(v: unknown) {
    this.value = v;
  }
  registerOnChange(fn: (v: unknown) => void) {
    this.change = fn;
  }
  registerOnTouched(fn: () => void) {
    this.touched = fn;
  }
  setDisabledState(v: boolean) {
    this.disabled = v;
  }
}
