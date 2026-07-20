import { Component, Inject } from "@angular/core";
import { FormsModule } from "@angular/forms";
import { DIALOG_DATA, DialogRef } from "@angular/cdk/dialog";
import {
  TvChannelService,
  TvChannelResetRulesPayload,
} from "@project-services/tv-channel.service";
import { FlwModalComponent } from "../../../ui/modal/flw-modal.component";
import { TranslateModule } from "@ngx-translate/core";

@Component({
  standalone: true,
  imports: [FormsModule, FlwModalComponent, TranslateModule],
  template: `
    <flw-modal
      [title]="'CHANNEL_DIALOGS.RESET.TITLE' | translate"
      [description]="data.channelName"
    >
      <p class="tooltip-note amber">
        {{ "CHANNEL_DIALOGS.RESET.WARNING" | translate }}
      </p>
      <fieldset>
        <legend>{{ "CHANNEL_DIALOGS.RESET.WHAT" | translate }}</legend>
        <label
          ><input type="checkbox" [(ngModel)]="nature" />
          {{ "CHANNEL_DIALOGS.RESET.NATURES" | translate }}</label
        ><label
          ><input type="checkbox" [(ngModel)]="kind" />
          {{ "CHANNEL_DIALOGS.RESET.KINDS" | translate }}</label
        ><label
          ><input type="checkbox" [(ngModel)]="category" />
          {{ "CHANNEL_DIALOGS.RESET.CATEGORIES" | translate }}</label
        ><label
          ><input type="checkbox" [(ngModel)]="genre" />
          {{ "CHANNEL_DIALOGS.RESET.GENRES" | translate }}</label
        ><label
          ><input type="checkbox" [(ngModel)]="tag" />
          {{ "CHANNEL_DIALOGS.RESET.TAGS" | translate }}</label
        >
      </fieldset>
      <fieldset>
        <legend>{{ "CHANNEL_DIALOGS.RESET.LEVEL" | translate }}</legend>
        <label
          ><input type="checkbox" [(ngModel)]="allowed" />
          {{ "CHANNEL_DIALOGS.COMMON.ALLOWED" | translate }}</label
        ><label
          ><input type="checkbox" [(ngModel)]="forbidden" />
          {{ "CHANNEL_DIALOGS.COMMON.FORBIDDEN" | translate }}</label
        >
      </fieldset>
      <div modal-footer>
        <button class="btn ghost" type="button" (click)="ref.close(false)">
          {{ "CHANNEL_DIALOGS.COMMON.CANCEL" | translate }}</button
        ><button
          class="btn danger-ghost"
          type="button"
          [disabled]="!valid"
          (click)="reset()"
        >
          {{ "CHANNEL_DIALOGS.RESET.ACTION" | translate }}
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
  genre = true;
  tag = true;
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
      (this.nature || this.kind || this.category || this.genre || this.tag) &&
      (this.allowed || this.forbidden)
    );
  }
  reset() {
    const payload: TvChannelResetRulesPayload = { types: [], levels: [] };
    if (this.nature) payload.types.push("nature");
    if (this.kind) payload.types.push("kind");
    if (this.category) payload.types.push("category");
    if (this.genre) payload.types.push("genre");
    if (this.tag) payload.types.push("tag");
    if (this.allowed) payload.levels.push("allowed");
    if (this.forbidden) payload.levels.push("forbidden");
    this.service.resetRules(this.data.channelId, payload).subscribe((r) => {
      if (r.isOk) this.ref.close(true);
    });
  }
}
