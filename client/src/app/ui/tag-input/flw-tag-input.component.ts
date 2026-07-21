import {
  Component,
  ElementRef,
  forwardRef,
  Input,
  OnDestroy,
  ViewChild,
} from "@angular/core";
import { NgFor, NgIf } from "@angular/common";
import {
  ControlValueAccessor,
  FormsModule,
  NG_VALUE_ACCESSOR,
} from "@angular/forms";
import { TranslateModule } from "@ngx-translate/core";
import { Observable, of, Subject } from "rxjs";
import { catchError, debounceTime, switchMap } from "rxjs/operators";
export interface FlwTagOption {
  label: string;
  value: string | number;
}
const SEARCH_MIN_CHARS = 2;
const SEARCH_DEBOUNCE_MS = 250;
@Component({
  selector: "flw-tag-input",
  standalone: true,
  imports: [NgFor, NgIf, FormsModule, TranslateModule],
  template: `<div
      class="tag-input"
      [attr.data-variant]="variant"
      [class.invalid]="invalidDraft"
    >
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
        (ngModelChange)="onDraftChange()"
        (keydown.enter)="addDraft($event)"
        (blur)="onBlur()"
        [placeholder]="'UI.TAG_INPUT.ADD' | translate"
      /><datalist [id]="listId">
        <option
          *ngFor="let option of filteredOptions"
          [value]="option.label"
        ></option>
      </datalist>
    </div>
    <span class="tag-input-error" *ngIf="invalidDraft">{{
      "UI.TAG_INPUT.INVALID" | translate
    }}</span>`,
  styles: [
    `
      .tag-input.invalid {
        border-color: var(--critical);
      }
      .tag-input-error {
        color: var(--critical);
        font-size: 11.5px;
      }
    `,
  ],
  providers: [
    {
      provide: NG_VALUE_ACCESSOR,
      useExisting: forwardRef(() => FlwTagInputComponent),
      multi: true,
    },
  ],
})
export class FlwTagInputComponent implements ControlValueAccessor, OnDestroy {
  @Input() variant: "allow" | "prefer" | "forbid" = "allow";
  @Input() options: FlwTagOption[] = [];
  @Input() freeText = false;
  // Autocompletion server-side : les resultats completent les options
  // statiques pendant la frappe (validation finale cote serveur).
  @Input() searchProvider?: (query: string) => Observable<FlwTagOption[]>;
  // Libelle de secours pour les valeurs hors options (axes recherches).
  @Input() labelFormatter?: (value: string | number) => string;
  // Parseur local pour les syntaxes structurees qui ne viennent pas de
  // l'autocompletion (par exemple min-age>10).
  @Input() draftParser?: (draft: string) => FlwTagOption | null;
  @ViewChild("input") input?: ElementRef<HTMLInputElement>;
  values: Array<string | number> = [];
  draft = "";
  disabled = false;
  invalidDraft = false;
  searchResults: FlwTagOption[] = [];
  readonly listId = `flw-tags-${Math.random().toString(36).slice(2)}`;
  private search$ = new Subject<string>();
  // Options deja proposees pendant la saisie : elles restent selectionnables
  // meme quand une frappe ulterieure (ex. selection datalist) vide les
  // resultats courants.
  private seenSearchOptions = new Map<string | number, FlwTagOption>();
  private searchSubscription = this.search$
    .pipe(
      debounceTime(SEARCH_DEBOUNCE_MS),
      switchMap((query) =>
        this.searchProvider && query.length >= SEARCH_MIN_CHARS
          ? this.searchProvider(query).pipe(catchError(() => of([])))
          : of([] as FlwTagOption[]),
      ),
    )
    .subscribe((results) => {
      this.searchResults = results;
      for (const option of results)
        this.seenSearchOptions.set(option.value, option);
    });
  private change = (v: Array<string | number>) => {};
  touched = () => {};
  private get matchableOptions() {
    return [...this.options, ...this.seenSearchOptions.values()];
  }
  get filteredOptions() {
    return [...this.options, ...this.searchResults].filter(
      (o) =>
        !this.values.includes(o.value) &&
        (!this.draft ||
          o.label.toLowerCase().includes(this.draft.toLowerCase())),
    );
  }
  labelFor(value: string | number) {
    return (
      this.matchableOptions.find((o) => o.value === value)?.label ??
      this.labelFormatter?.(value) ??
      String(value)
    );
  }
  onDraftChange() {
    this.invalidDraft = false;
    this.search$.next(this.draft.trim());
  }
  addDraft(event?: Event) {
    event?.preventDefault();
    const text = this.draft.trim();
    const option =
      this.findOption(text) ?? this.draftParser?.(text) ?? undefined;
    if (option) this.seenSearchOptions.set(option.value, option);
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
  // Accepte le label complet ("Studio=Warner Bros.") ou la valeur seule
  // ("Warner Bros.") telle que l'utilisateur la tape naturellement.
  private findOption(text: string) {
    const query = text.toLowerCase();
    if (!query) return undefined;
    return this.matchableOptions.find((o) => {
      const label = o.label.toLowerCase();
      if (label === query) return true;
      const separator = label.indexOf("=");
      return separator >= 0 && label.slice(separator + 1) === query;
    });
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
  ngOnDestroy() {
    this.searchSubscription.unsubscribe();
  }
}
