import { Component, Inject } from "@angular/core";
import {
  FormControl,
  FormGroup,
  ReactiveFormsModule,
  Validators,
} from "@angular/forms";
import { DIALOG_DATA, DialogRef } from "@angular/cdk/dialog";
import { Catalog } from "@project-interfaces/catalog";
import { TvChannel } from "@project-interfaces/tv-channel";
import { TvChannelService } from "@project-services/tv-channel.service";
import { FlwModalComponent } from "../../../ui/modal/flw-modal.component";
import { FlwSelectComponent } from "../../../ui/select/flw-select.component";
import { FlwSwitchComponent } from "../../../ui/switch/flw-switch.component";
import { TranslateModule } from "@ngx-translate/core";
@Component({
  standalone: true,
  imports: [
    ReactiveFormsModule,
    FlwModalComponent,
    FlwSelectComponent,
    FlwSwitchComponent,
    TranslateModule,
  ],
  template: `<flw-modal
    [title]="
      (data.channel ? 'CHANNELS.EDIT_CHANNEL' : 'CHANNELS.NEW_CHANNEL')
        | translate
    "
    ><form [formGroup]="form">
      <div class="field">
        <label>{{ "COMMON.NAME" | translate }}</label
        ><input formControlName="name" type="text" />
      </div>
      <div class="field">
        <label>{{ "COMMON.DESCRIPTION" | translate }}</label
        ><textarea formControlName="description" rows="4"></textarea>
      </div>
      <div class="field">
        <label>{{ "CHANNELS.CATALOG_LABEL" | translate }}</label
        ><flw-select formControlName="catalog" [options]="catalogOptions" />
      </div>
      <flw-switch
        formControlName="is_enabled"
        [label]="'CHANNELS.CHANNEL_ACTIVE' | translate"
      />
    </form>
    <div modal-footer>
      <span></span>
      <div>
        <button class="btn ghost" (click)="ref.close()">
          {{ "COMMON.CANCEL" | translate }}</button
        ><button class="btn primary" (click)="save()">
          {{ "CHANNEL_DIALOGS.COMMON.SAVE" | translate }}
        </button>
      </div>
    </div></flw-modal
  >`,
  styles: [
    `
      form {
        display: grid;
        gap: 14px;
      }
    `,
  ],
})
export class TvChannelDialogComponent {
  catalogOptions = this.data.catalogs.map((c) => ({
    label: c.name,
    value: c.id,
  }));
  form = new FormGroup({
    name: new FormControl(this.data.channel?.name ?? "", {
      nonNullable: true,
      validators: [Validators.required],
    }),
    description: new FormControl(this.data.channel?.description ?? ""),
    catalog: new FormControl(
      this.data.channel?.catalog ?? this.data.selectedCatalogId,
      { validators: [Validators.required] },
    ),
    is_enabled: new FormControl(this.data.channel?.is_enabled ?? true, {
      nonNullable: true,
    }),
  });
  constructor(
    private service: TvChannelService,
    public ref: DialogRef<boolean>,
    @Inject(DIALOG_DATA)
    public data: {
      channel?: TvChannel;
      selectedCatalogId: string | null;
      catalogs: Catalog[];
    },
  ) {}
  save() {
    if (this.form.invalid) return;
    const req = this.data.channel
      ? this.service.patchObject(
          String(this.data.channel.id),
          this.form.getRawValue(),
        )
      : this.service.createObject(this.form.getRawValue());
    req.subscribe((r) => {
      if (r.isOk) this.ref.close(true);
    });
  }
}
