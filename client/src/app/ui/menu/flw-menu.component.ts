import { Component, ElementRef, HostListener, Input } from "@angular/core";
import { FlwIconComponent } from "../icon/flw-icon.component";
@Component({
  selector: "flw-menu",
  standalone: true,
  imports: [FlwIconComponent],
  template: `<details class="menu" #menu>
    <summary class="btn ghost icon-only" [attr.aria-label]="label">
      <flw-icon name="kebab" />
    </summary>
    <div class="menu-panel" (click)="close()"><ng-content /></div>
  </details>`,
})
export class FlwMenuComponent {
  @Input() label = "Actions";
  constructor(private host: ElementRef<HTMLElement>) {}
  close() {
    this.host.nativeElement.querySelector("details")?.removeAttribute("open");
  }
  @HostListener("document:click", ["$event"]) outside(e: Event) {
    if (!this.host.nativeElement.contains(e.target as Node)) this.close();
  }
}
