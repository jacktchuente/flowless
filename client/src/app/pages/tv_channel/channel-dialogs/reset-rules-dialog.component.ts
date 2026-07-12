import { Component, Inject } from "@angular/core";
import { FormsModule } from "@angular/forms";
import { DIALOG_DATA, DialogRef } from "@angular/cdk/dialog";
import {
  TvChannelService,
  TvChannelResetRulesPayload,
} from "@project-services/tv-channel.service";
import { FlwModalComponent } from "../../../ui/modal/flw-modal.component";

@Component({
  standalone: true,
  imports: [FormsModule, FlwModalComponent],
  template: `
    <flw-modal
      title="Réinitialiser des règles"
      [description]="data.channelName"
    >
      <p class="tooltip-note amber">Cette opération est irréversible.</p>
      <fieldset>
        <legend>Quoi</legend>
        <label><input type="checkbox" [(ngModel)]="nature" /> Natures</label
        ><label
          ><input type="checkbox" [(ngModel)]="kind" /> Types de
          contenant</label
        ><label
          ><input type="checkbox" [(ngModel)]="category" /> Catégories</label
        >
      </fieldset>
      <fieldset>
        <legend>Quel niveau</legend>
        <label><input type="checkbox" [(ngModel)]="allowed" /> Autorisé</label
        ><label
          ><input type="checkbox" [(ngModel)]="forbidden" /> Interdit</label
        >
      </fieldset>
      <div modal-footer>
        <button class="btn ghost" type="button" (click)="ref.close(false)">
          Annuler</button
        ><button
          class="btn danger-ghost"
          type="button"
          [disabled]="!valid"
          (click)="reset()"
        >
          Réinitialiser la sélection
        </button>
      </div>
    </flw-modal>
  `,
  styles: [
    `
      fieldset {
        display: grid;
        gap: 8px;
        border: 1px solid var(--slate-100);
        border-radius: var(--radius-m);
        padding: 14px;
      }
      legend {
        font-weight: 600;
      }
    `,
  ],
})
export class ResetRulesDialogComponent {
  nature = true;
  kind = true;
  category = true;
  allowed = true;
  forbidden = true;
  constructor(
    private service: TvChannelService,
    public ref: DialogRef<boolean>,
    @Inject(DIALOG_DATA)
    public data: { channelId: string | number; channelName: string },
  ) {}
  get valid() {
    return (
      (this.nature || this.kind || this.category) &&
      (this.allowed || this.forbidden)
    );
  }
  reset() {
    const payload: TvChannelResetRulesPayload = { types: [], levels: [] };
    if (this.nature) payload.types.push("nature");
    if (this.kind) payload.types.push("kind");
    if (this.category) payload.types.push("category");
    if (this.allowed) payload.levels.push("allowed");
    if (this.forbidden) payload.levels.push("forbidden");
    this.service.resetRules(this.data.channelId, payload).subscribe((r) => {
      if (r.isOk) this.ref.close(true);
    });
  }
}
