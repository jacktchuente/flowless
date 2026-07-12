import {
  Component,
  ElementRef,
  forwardRef,
  Input,
  ViewChild,
} from "@angular/core";
import { NgFor } from "@angular/common";
import {
  ControlValueAccessor,
  FormsModule,
  NG_VALUE_ACCESSOR,
} from "@angular/forms";
export interface FlwTagOption {
  label: string;
  value: string | number;
}
@Component({
  selector: "flw-tag-input",
  standalone: true,
  imports: [NgFor, FormsModule],
  template: `<div class="tag-input" [attr.data-variant]="variant">
    <span class="tag" [class]="variant" *ngFor="let value of values"
      ><span>{{ labelFor(value) }}</span
      ><button
        type="button"
        [attr.aria-label]="'Retirer ' + labelFor(value)"
        (click)="remove(value)"
      >
        ✕
      </button></span
    ><input
      #input
      [disabled]="disabled"
      [(ngModel)]="draft"
      [attr.list]="listId"
      (keydown.enter)="addDraft($event)"
      (blur)="onBlur()"
      placeholder="Ajouter…"
    /><datalist [id]="listId">
      <option
        *ngFor="let option of filteredOptions"
        [value]="option.label"
      ></option>
    </datalist>
  </div>`,
  providers: [
    {
      provide: NG_VALUE_ACCESSOR,
      useExisting: forwardRef(() => FlwTagInputComponent),
      multi: true,
    },
  ],
})
export class FlwTagInputComponent implements ControlValueAccessor {
  @Input() variant: "allow" | "prefer" | "forbid" = "allow";
  @Input() options: FlwTagOption[] = [];
  @Input() freeText = false;
  @ViewChild("input") input?: ElementRef<HTMLInputElement>;
  values: Array<string | number> = [];
  draft = "";
  disabled = false;
  readonly listId = `flw-tags-${Math.random().toString(36).slice(2)}`;
  private change = (v: Array<string | number>) => {};
  touched = () => {};
  get filteredOptions() {
    return this.options.filter(
      (o) =>
        !this.values.includes(o.value) &&
        (!this.draft ||
          o.label.toLowerCase().includes(this.draft.toLowerCase())),
    );
  }
  labelFor(value: string | number) {
    return this.options.find((o) => o.value === value)?.label ?? String(value);
  }
  addDraft(event?: Event) {
    event?.preventDefault();
    const text = this.draft.trim();
    const option = this.options.find(
      (o) => o.label.toLowerCase() === text.toLowerCase(),
    );
    if (
      (option || (this.freeText && text)) &&
      !this.values.includes(option?.value ?? text)
    ) {
      this.values = [...this.values, option?.value ?? text];
      this.change(this.values);
    }
    this.draft = "";
  }
  remove(value: string | number) {
    this.values = this.values.filter((v) => v !== value);
    this.change(this.values);
    this.touched();
  }
  onBlur() {
    if (this.freeText) this.addDraft();
    this.touched();
  }
  writeValue(v: Array<string | number> | null) {
    this.values = Array.isArray(v) ? [...v] : [];
  }
  registerOnChange(fn: (v: Array<string | number>) => void) {
    this.change = fn;
  }
  registerOnTouched(fn: () => void) {
    this.touched = fn;
  }
  setDisabledState(v: boolean) {
    this.disabled = v;
  }
}
