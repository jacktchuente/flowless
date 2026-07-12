import { NgIf } from "@angular/common";
import { Component, DestroyRef, Inject, inject } from "@angular/core";
import { DIALOG_DATA, DialogRef } from "@angular/cdk/dialog";
import { FormsModule } from "@angular/forms";
import { filter } from "rxjs";
import { takeUntilDestroyed } from "@angular/core/rxjs-interop";
import { WebsocketService } from "@kwyxyz/ngx-request";
import { TvChannelService } from "@project-services/tv-channel.service";
import { FlwModalComponent } from "../../../ui/modal/flw-modal.component";
import { FlwSwitchComponent } from "../../../ui/switch/flw-switch.component";
import { FlwSelectComponent } from "../../../ui/select/flw-select.component";
import { FlwGenStepsComponent } from "../../../ui/gen-steps/flw-gen-steps.component";
import { TranslateModule, TranslateService } from "@ngx-translate/core";

export interface GenerationDialogData {
  channelId: string | number;
  channelName: string;
  kind: "blueprint" | "playout";
}

@Component({
  standalone: true,
  imports: [
    NgIf,
    FormsModule,
    FlwModalComponent,
    FlwSwitchComponent,
    FlwSelectComponent,
    FlwGenStepsComponent,
    TranslateModule,
  ],
  template: `
    <flw-modal [title]="title" [description]="description">
      <ng-container *ngIf="state === 'idle'">
        <ng-container *ngIf="data.kind === 'blueprint'; else playoutFields">
          <div class="field">
            <label>{{ "CHANNEL_DIALOGS.GENERATION.METHOD" | translate }}</label
            ><flw-select [(ngModel)]="method" [options]="methods" />
          </div>
          <flw-switch
            [(ngModel)]="gridOnly"
            [label]="'CHANNEL_DIALOGS.GENERATION.GRID_ONLY' | translate"
          />
          <flw-switch
            [(ngModel)]="reboot"
            [label]="'CHANNEL_DIALOGS.GENERATION.REBOOT' | translate"
          />
        </ng-container>
        <ng-template #playoutFields>
          <div class="field">
            <label>{{ "CHANNEL_DIALOGS.GENERATION.DAYS" | translate }}</label
            ><input
              class="mono"
              type="number"
              min="1"
              max="31"
              [(ngModel)]="days"
            />
          </div>
          <flw-switch
            [(ngModel)]="reset"
            [label]="'CHANNEL_DIALOGS.GENERATION.RESET' | translate"
          />
        </ng-template>
      </ng-container>
      <flw-gen-steps *ngIf="state !== 'idle'" [steps]="steps" [state]="state" />
      <p class="tooltip-note amber" *ngIf="state === 'error'">
        {{ "CHANNEL_DIALOGS.GENERATION.ERROR" | translate }}
      </p>
      <div modal-footer>
        <span></span>
        <div class="actions">
          <button
            class="btn ghost"
            type="button"
            (click)="ref.close(state === 'done')"
          >
            {{
              (state === "running"
                ? "CHANNEL_DIALOGS.GENERATION.HIDE"
                : "CHANNEL_DIALOGS.COMMON.CLOSE"
              ) | translate
            }}
          </button>
          <button
            class="btn primary"
            type="button"
            *ngIf="state === 'idle'"
            (click)="start()"
          >
            {{ "CHANNEL_DIALOGS.GENERATION.START" | translate }}
          </button>
        </div>
      </div>
    </flw-modal>
  `,
  styles: [
    `
      .actions {
        display: flex;
        gap: 8px;
      }
    `,
  ],
})
export class GenerationDialogComponent {
  private destroyRef = inject(DestroyRef);
  state: "idle" | "running" | "done" | "error" = "idle";
  method: "full_llm" | "random" | "preset_and_llm" = "preset_and_llm";
  methods: Array<{ label: string; value: string }> = [];
  gridOnly = false;
  reboot = false;
  days = 7;
  reset = false;
  private timeout?: ReturnType<typeof setTimeout>;

  constructor(
    private service: TvChannelService,
    private translate: TranslateService,
    ws: WebsocketService,
    public ref: DialogRef<boolean>,
    @Inject(DIALOG_DATA) public data: GenerationDialogData,
  ) {
    this.methods = [
      {
        label: this.translate.instant("CHANNEL_DIALOGS.GENERATION.AI"),
        value: "full_llm",
      },
      {
        label: this.translate.instant("CHANNEL_DIALOGS.GENERATION.PRESET"),
        value: "preset_and_llm",
      },
      {
        label: this.translate.instant("CHANNEL_DIALOGS.GENERATION.RANDOM"),
        value: "random",
      },
    ];
    ws.crudEvent
      .pipe(
        filter(
          (event: any) =>
            event.type?.toLowerCase?.() === "tvchannel" &&
            String(event.id) === String(data.channelId),
        ),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe(() => {
        if (this.state === "running") this.checkChannelState();
      });
  }

  get title() {
    return this.translate.instant(
      this.data.kind === "blueprint"
        ? "CHANNEL_DIALOGS.GENERATION.BLUEPRINT_TITLE"
        : "CHANNEL_DIALOGS.GENERATION.PLAYOUT_TITLE",
    );
  }
  get description() {
    return this.translate.instant("CHANNEL_DIALOGS.GENERATION.CHANNEL", {
      name: this.data.channelName,
    });
  }
  get steps() {
    const steps =
      this.data.kind === "blueprint"
        ? ["READ_COLLECTIONS", "BUILD_BLOCKS", "CHECK_RULES", "WRITE_GRID"]
        : ["READ_RULES", "SELECT_MEDIA", "RESOLVE", "WRITE_PLAYOUT"];
    return steps.map((step) =>
      this.translate.instant(`CHANNEL_DIALOGS.GENERATION.STEPS.${step}`),
    );
  }

  start() {
    this.state = "running";
    const request =
      this.data.kind === "blueprint"
        ? this.service.generateBlueprint(this.data.channelId, {
            grid_generation_mode: this.method,
            grid_only: this.gridOnly,
            reboot: this.reboot,
          })
        : this.service.generatePlayout(this.data.channelId, {
            days: this.days,
            reset: this.reset,
          });
    request.subscribe((response) => {
      if (!response.isOk) this.state = "error";
    });
    this.timeout = setTimeout(
      () => {
        if (this.state === "running") this.state = "error";
      },
      15 * 60 * 1000,
    );
  }

  private checkChannelState() {
    this.service.getDetail(this.data.channelId).subscribe((response) => {
      if (!response.isOk || this.state !== "running") return;
      const status = String(
        (response.body as { analyze_status?: unknown }).analyze_status ?? "",
      ).toUpperCase();
      if (["1", "ANALYZING", "RUNNING"].includes(status)) return;
      this.state =
        status === "4" ||
        status === "5" ||
        status.includes("ERROR") ||
        status.includes("CANCEL")
          ? "error"
          : "done";
      if (this.timeout) clearTimeout(this.timeout);
    });
  }
}
