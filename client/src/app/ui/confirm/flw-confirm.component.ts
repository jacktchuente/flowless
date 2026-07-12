import { Component, Inject } from "@angular/core";
import { NgIf } from "@angular/common";
import { DIALOG_DATA, DialogRef } from "@angular/cdk/dialog";
import { FlwModalComponent } from "../modal/flw-modal.component";
import { TranslateModule } from "@ngx-translate/core";
export interface FlwConfirmData {
  title: string;
  message: string;
  confirmLabel?: string;
  /** Avertissement affiché sous le message. */
  warning?: string;
  /** Action alternative (ex. « Oui, tout réanalyser ») : ferme avec "extra". */
  extraLabel?: string;
}
export type FlwConfirmResult = boolean | "extra";
@Component({
  standalone: true,
  imports: [NgIf, FlwModalComponent, TranslateModule],
  template: `<flw-modal [title]="data.title"
    ><p>{{ data.message }}</p>
    <p class="tooltip-note amber" *ngIf="data.warning">{{ data.warning }}</p>
    <div modal-footer>
      <button
        class="btn danger-ghost"
        type="button"
        *ngIf="data.extraLabel"
        (click)="ref.close('extra')"
      >
        {{ data.extraLabel }}
      </button>
      <span *ngIf="!data.extraLabel"></span>
      <div>
        <button class="btn ghost" type="button" (click)="ref.close(false)">
          {{ "COMMON.CANCEL" | translate }}</button
        ><button class="btn primary" type="button" (click)="ref.close(true)">
          {{ data.confirmLabel || ("COMMON.CONFIRM" | translate) }}
        </button>
      </div>
    </div></flw-modal
  >`,
})
export class FlwConfirmComponent {
  constructor(
    @Inject(DIALOG_DATA) public data: FlwConfirmData,
    public ref: DialogRef<FlwConfirmResult>,
  ) {}
}
