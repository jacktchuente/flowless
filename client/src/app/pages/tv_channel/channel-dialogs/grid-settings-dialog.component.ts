import { Component, Inject } from "@angular/core";
import { FormsModule } from "@angular/forms";
import { DIALOG_DATA, DialogRef } from "@angular/cdk/dialog";
import { FormOptions } from "@project-interfaces/tv-channel";
import { TvChannelService } from "@project-services/tv-channel.service";
import { FlwModalComponent } from "../../../ui/modal/flw-modal.component";
import { FlwSelectComponent } from "../../../ui/select/flw-select.component";
@Component({
  standalone: true,
  imports: [FormsModule, FlwModalComponent, FlwSelectComponent],
  template: `<flw-modal title="Paramètres de la grille"
    ><div class="field">
      <label>Politique de remplissage</label
      ><flw-select [(ngModel)]="policy" [options]="options" />
    </div>
    <div modal-footer>
      <button class="btn ghost" (click)="ref.close(false)">Annuler</button
      ><button class="btn primary" (click)="save()">Enregistrer</button>
    </div></flw-modal
  >`,
})
export class GridSettingsDialogComponent {
  policy: string | number | null;
  options: { label: string; value: string | number | null }[];
  constructor(
    private service: TvChannelService,
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
      { label: "Non", value: null },
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
