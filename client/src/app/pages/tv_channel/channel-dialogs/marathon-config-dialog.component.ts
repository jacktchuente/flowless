import { Component, Inject } from "@angular/core";
import { NgFor, NgIf } from "@angular/common";
import { FormsModule } from "@angular/forms";
import { DIALOG_DATA, DialogRef } from "@angular/cdk/dialog";
import {
  FormOptions,
  MarathonKindPolicy,
} from "@project-interfaces/tv-channel";
import { TvChannelService } from "@project-services/tv-channel.service";
import { NotificationService } from "@project-shared/services/notification.service";
import { FlwIconComponent } from "../../../ui/icon/flw-icon.component";
import { FlwModalComponent } from "../../../ui/modal/flw-modal.component";
import { FlwSelectComponent } from "../../../ui/select/flw-select.component";
import { TranslateModule } from "@ngx-translate/core";

@Component({
  standalone: true,
  imports: [
    NgFor,
    NgIf,
    FormsModule,
    FlwIconComponent,
    FlwModalComponent,
    FlwSelectComponent,
    TranslateModule,
  ],
  template: `<flw-modal
    [title]="'CHANNEL_DIALOGS.MARATHON.TITLE' | translate"
  >
    <p class="desc">{{ "CHANNEL_DIALOGS.MARATHON.DESC" | translate }}</p>
    <div class="policy-head" *ngIf="policies.length">
      <span>{{ "CHANNEL_DIALOGS.MARATHON.KIND" | translate }}</span>
      <span>{{ "CHANNEL_DIALOGS.MARATHON.MIN_RUN" | translate }}</span>
      <span>{{ "CHANNEL_DIALOGS.MARATHON.MAX_RUN" | translate }}</span>
      <span>{{ "CHANNEL_DIALOGS.MARATHON.QUOTA" | translate }}</span>
      <span></span>
    </div>
    <div class="policy-row" *ngFor="let policy of policies; let i = index">
      <flw-select
        [ngModel]="policy.container_kind"
        (ngModelChange)="policy.container_kind = +$event"
        [options]="kindOptions(policy)"
      />
      <input type="number" min="0" [(ngModel)]="policy.min_run" />
      <input type="number" min="0" [(ngModel)]="policy.max_run" />
      <input type="number" min="1" [(ngModel)]="policy.quota" />
      <button
        class="btn sm icon-only ghost"
        type="button"
        (click)="removeRow(i)"
        [attr.aria-label]="'CHANNEL_DIALOGS.MARATHON.REMOVE_KIND' | translate"
      >
        <flw-icon name="trash" />
      </button>
    </div>
    <div class="empty" *ngIf="!policies.length">
      {{ "CHANNEL_DIALOGS.MARATHON.NO_KIND" | translate }}
    </div>
    <button
      class="btn sm ghost"
      type="button"
      [disabled]="!availableKinds().length"
      (click)="addRow()"
    >
      <flw-icon name="plus" />{{
        "CHANNEL_DIALOGS.MARATHON.ADD_KIND" | translate
      }}
    </button>
    <p class="error" *ngIf="error">{{ error | translate }}</p>
    <div modal-footer>
      <button class="btn ghost" (click)="ref.close(false)">
        {{ "CHANNEL_DIALOGS.COMMON.CANCEL" | translate }}</button
      ><button class="btn primary" (click)="save()">
        {{ "CHANNEL_DIALOGS.COMMON.SAVE" | translate }}
      </button>
    </div></flw-modal
  >`,
  styles: [
    `
      .desc {
        margin: 0 0 12px;
        color: var(--text-muted, #888);
      }
      .policy-head,
      .policy-row {
        display: grid;
        grid-template-columns: 2fr 1fr 1fr 1fr 32px;
        gap: 8px;
        align-items: center;
        margin-bottom: 8px;
      }
      .policy-head span {
        font-size: 12px;
        color: var(--text-muted, #888);
      }
      .empty {
        margin: 8px 0;
        color: var(--text-muted, #888);
      }
      .error {
        color: var(--danger, #d33);
        margin: 8px 0 0;
      }
    `,
  ],
})
export class MarathonConfigDialogComponent {
  policies: MarathonKindPolicy[];
  error = "";
  constructor(
    private service: TvChannelService,
    private notification: NotificationService,
    public ref: DialogRef<boolean>,
    @Inject(DIALOG_DATA)
    public data: {
      channelId: string | number;
      policies: MarathonKindPolicy[];
      formOptions: FormOptions;
    },
  ) {
    this.policies = data.policies.map((policy) => ({ ...policy }));
  }
  kindOptions(current: MarathonKindPolicy) {
    const used = new Set(
      this.policies
        .filter((policy) => policy !== current)
        .map((policy) => policy.container_kind),
    );
    return this.data.formOptions.container_kinds
      .filter(
        (option) =>
          option.value === current.container_kind || !used.has(option.value),
      )
      .map((option) => ({ label: option.label, value: option.value }));
  }
  availableKinds() {
    const used = new Set(this.policies.map((policy) => policy.container_kind));
    return this.data.formOptions.container_kinds.filter(
      (option) => !used.has(option.value),
    );
  }
  addRow() {
    const kind = this.availableKinds()[0];
    if (!kind) return;
    this.policies.push({
      container_kind: kind.value,
      min_run: 1,
      max_run: 1,
      quota: 1,
    });
  }
  removeRow(index: number) {
    this.policies.splice(index, 1);
  }
  save() {
    this.error = "";
    const invalid = this.policies.some(
      (policy) =>
        policy.max_run > 0 && policy.min_run > policy.max_run,
    );
    if (invalid) {
      this.error = "CHANNEL_DIALOGS.MARATHON.MIN_ABOVE_MAX";
      return;
    }
    this.service
      .updateMarathonConfig(this.data.channelId, {
        kind_policies: this.policies.map(
          ({ container_kind, min_run, max_run, quota }) => ({
            container_kind,
            min_run,
            max_run,
            quota,
          }),
        ),
      })
      .subscribe((r) => {
        if (r.isOk) {
          this.ref.close(true);
          return;
        }
        this.notification.notify("CHANNEL_DIALOGS.MARATHON.NOTIFY_SAVE_FAILED");
      });
  }
}
