import {
  Component,
  EventEmitter,
  forwardRef,
  Input,
  Output,
} from "@angular/core";
import { NgFor } from "@angular/common";
import { ControlValueAccessor, NG_VALUE_ACCESSOR } from "@angular/forms";
export interface FlwSelectOption {
  label: string;
  value: unknown;
  disabled?: boolean;
}
@Component({
  selector: "flw-select",
  standalone: true,
  imports: [NgFor],
  template: `<div class="select-fake">
    <select
      [disabled]="disabled"
      [value]="serialized(value)"
      (change)="select($any($event.target).value)"
      (blur)="touched()"
    >
      <option
        *ngFor="let option of options; let i = index"
        [value]="i"
        [disabled]="option.disabled"
      >
        {{ option.label }}
      </option>
    </select>
  </div>`,
  providers: [
    {
      provide: NG_VALUE_ACCESSOR,
      useExisting: forwardRef(() => FlwSelectComponent),
      multi: true,
    },
  ],
})
export class FlwSelectComponent implements ControlValueAccessor {
  @Input() options: FlwSelectOption[] = [];
  @Input() value: unknown;
  @Output() valueChange = new EventEmitter<unknown>();
  disabled = false;
  private change = (v: unknown) => {};
  touched = () => {};
  serialized(v: unknown) {
    const i = this.options.findIndex((o) => o.value === v);
    return i < 0 ? "" : String(i);
  }
  select(index: string) {
    const option = this.options[Number(index)];
    if (option) {
      this.value = option.value;
      this.change(this.value);
      this.valueChange.emit(this.value);
    }
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
