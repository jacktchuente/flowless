import { Component, Inject } from "@angular/core";
import { NgIf } from "@angular/common";
import {
  FormControl,
  FormGroup,
  ReactiveFormsModule,
  Validators,
} from "@angular/forms";
import { DIALOG_DATA, DialogRef } from "@angular/cdk/dialog";
import { Catalog } from "@project-interfaces/catalog";
import { TvChannel } from "@project-interfaces/tv-channel";
import {
  TvChannelNameSuggestionResponse,
  TvChannelService,
} from "@project-services/tv-channel.service";
import { NotificationService } from "@project-shared/services/notification.service";
import { FlwIconComponent } from "../../../ui/icon/flw-icon.component";
import { FlwModalComponent } from "../../../ui/modal/flw-modal.component";
import { FlwSelectComponent } from "../../../ui/select/flw-select.component";
import { FlwSwitchComponent } from "../../../ui/switch/flw-switch.component";
import { TranslateModule } from "@ngx-translate/core";
@Component({
  standalone: true,
  imports: [
    NgIf,
    ReactiveFormsModule,
    FlwIconComponent,
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
        <label>{{ "COMMON.NAME" | translate }}</label>
        <div class="name-row">
          <input formControlName="name" type="text" />
          <button
            class="btn sm ghost"
            type="button"
            *ngIf="data.channel"
            [disabled]="isSuggestingName"
            (click)="suggestName()"
          >
            <flw-icon name="generate" />{{
              "TV_CHANNEL_DIALOG.SUGGEST_NAME" | translate
            }}
          </button>
        </div>
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
      .name-row {
        display: flex;
        align-items: center;
        gap: 8px;
      }
      .name-row input {
        flex: 1;
      }
    `,
  ],
})
export class TvChannelDialogComponent {
  isSuggestingName = false;
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
    private notification: NotificationService,
    public ref: DialogRef<boolean>,
    @Inject(DIALOG_DATA)
    public data: {
      channel?: TvChannel;
      selectedCatalogId: string | null;
      catalogs: Catalog[];
    },
  ) {}
  suggestName() {
    if (!this.data.channel || this.isSuggestingName) return;
    this.isSuggestingName = true;
    this.service.suggestName(this.data.channel.id).subscribe((response) => {
      this.isSuggestingName = false;
      const body = response.body as TvChannelNameSuggestionResponse | null;
      const name = body?.name?.trim();
      if (!response.isOk || !name) {
        this.notification.notify(
          "TV_CHANNEL_DIALOG.NOTIFY_SUGGEST_NAME_FAILED",
        );
        return;
      }
      this.form.controls.name.setValue(name);
      this.form.controls.name.markAsDirty();
    });
  }
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
