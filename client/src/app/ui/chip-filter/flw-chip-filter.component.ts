import { Component, EventEmitter, Input, Output } from "@angular/core";
@Component({
  selector: "flw-chip-filter",
  standalone: true,
  template: `<span class="chip-filter"
    >{{ label
    }}<button
      type="button"
      aria-label="Retirer le filtre"
      (click)="remove.emit()"
    >
      ✕
    </button></span
  >`,
})
export class FlwChipFilterComponent {
  @Input() label = "";
  @Output() remove = new EventEmitter<void>();
}
