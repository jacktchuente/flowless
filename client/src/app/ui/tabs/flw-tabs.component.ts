import { Component, EventEmitter, Input, Output } from "@angular/core";
import { NgFor } from "@angular/common";
export interface FlwTab {
  id: string;
  label: string;
}
@Component({
  selector: "flw-tabs",
  standalone: true,
  imports: [NgFor],
  template: `<nav class="tabs" role="tablist">
    <button
      type="button"
      role="tab"
      *ngFor="let tab of tabs"
      [class.active]="tab.id === active"
      [attr.aria-selected]="tab.id === active"
      (click)="select(tab.id)"
    >
      {{ tab.label }}
    </button>
  </nav>`,
})
export class FlwTabsComponent {
  @Input() tabs: FlwTab[] = [];
  @Input() active = "";
  @Output() activeChange = new EventEmitter<string>();
  select(id: string) {
    this.active = id;
    this.activeChange.emit(id);
  }
}
