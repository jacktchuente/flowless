import { Component, Inject } from "@angular/core";
import { FormsModule } from "@angular/forms";
import { DIALOG_DATA, DialogRef } from "@angular/cdk/dialog";
import { FormOptions } from "@project-interfaces/tv-channel";
import { TvChannelService } from "@project-services/tv-channel.service";
import { FlwModalComponent } from "../../../ui/modal/flw-modal.component";
import { FlwSelectComponent } from "../../../ui/select/flw-select.component";
import { TranslateModule, TranslateService } from "@ngx-translate/core";
@Component({
  standalone: true,
  imports: [
    FormsModule,
    FlwModalComponent,
    FlwSelectComponent,
    TranslateModule,
  ],
  template: `<flw-modal [title]="'CHANNEL_DIALOGS.GRID.SETTINGS' | translate"
    ><div class="field">
      <label>{{ "CHANNEL_DIALOGS.GRID.FILLER_POLICY" | translate }}</label
      ><flw-select [(ngModel)]="policy" [options]="options" />
    </div>
    <div modal-footer>
      <button class="btn ghost" (click)="ref.close(false)">
        {{ "CHANNEL_DIALOGS.COMMON.CANCEL" | translate }}</button
      ><button class="btn primary" (click)="save()">
        {{ "CHANNEL_DIALOGS.COMMON.SAVE" | translate }}
      </button>
    </div></flw-modal
  >`,
})
export class GridSettingsDialogComponent {
  policy: string | number | null;
  options: { label: string; value: string | number | null }[];
  constructor(
    private service: TvChannelService,
    private translate: TranslateService,
    public ref: DialogRef<boolean>,
    @Inject(DIALOG_DATA)
    public data: {
      channelId: string | number;
      policy: string | number | null;
      formOptions: FormOptions;
    },
  ) {
    this.policy = data.policy;
    this.options = [
      {
        label: this.translate.instant("CHANNEL_DIALOGS.GRID.NONE"),
        value: null,
      },
      ...data.formOptions.filler_policies.map((p) => ({
        label: `${p.name} (${p.duration_seconds}s)`,
        value: p.id,
      })),
    ];
  }
  save() {
    this.service
      .updateGrid(this.data.channelId, { post_filler_policy: this.policy })
      .subscribe((r) => {
        if (r.isOk) this.ref.close(true);
      });
  }
}
