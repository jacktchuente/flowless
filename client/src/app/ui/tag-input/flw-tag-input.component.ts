import {
  Component,
  ElementRef,
  forwardRef,
  Input,
  ViewChild,
} from "@angular/core";
import { NgFor, NgIf } from "@angular/common";
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
  imports: [NgFor, NgIf, FormsModule],
  template: `<div class="tag-input" [attr.data-variant]="variant" [class.invalid]="invalidDraft">
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
      (ngModelChange)="invalidDraft = false"
      (keydown.enter)="addDraft($event)"
      (blur)="onBlur()"
      placeholder="Ajouter…"
    /><datalist [id]="listId">
      <option
        *ngFor="let option of filteredOptions"
        [value]="option.label"
      ></option>
    </datalist>
  </div><span class="tag-input-error" *ngIf="invalidDraft">Choisissez une valeur proposée.</span>`,
  styles: [`.tag-input.invalid{border-color:var(--critical)}.tag-input-error{color:var(--critical);font-size:11.5px}`],
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
  invalidDraft = false;
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
    const canAdd =
      (option || (this.freeText && text)) &&
      !this.values.includes(option?.value ?? text);
    if (canAdd) {
      this.values = [...this.values, option?.value ?? text];
      this.change(this.values);
    } else if (text && !this.freeText) {
      this.invalidDraft = true;
    }
    if (canAdd) this.draft = "";
    this.touched();
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
