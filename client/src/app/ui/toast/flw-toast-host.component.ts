import { AsyncPipe, NgFor, NgIf } from "@angular/common";
import { Component } from "@angular/core";
import { ToastService } from "./toast.service";
@Component({
  selector: "flw-toast-host",
  standalone: true,
  imports: [AsyncPipe, NgFor, NgIf],
  template: `<div class="toast-host" aria-live="polite">
    <div class="toast" *ngFor="let toast of service.toasts$ | async">
      <span
        class="dot"
        [style.background]="
          toast.kind === 'error'
            ? 'var(--critical)'
            : toast.kind === 'info'
              ? 'var(--info)'
              : 'var(--success)'
        "
      ></span
      ><span>{{ toast.message }}</span
      ><button *ngIf="toast.action" type="button" (click)="service.act(toast)">
        {{ toast.action }}</button
      ><button
        *ngIf="!toast.action"
        type="button"
        aria-label="Fermer"
        (click)="service.dismiss(toast.id)"
      >
        ✕
      </button>
    </div>
  </div>`,
})
export class FlwToastHostComponent {
  constructor(public service: ToastService) {}
}
