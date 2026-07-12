import { Component, Inject } from "@angular/core";
import { NgIf } from "@angular/common";
import { DIALOG_DATA, DialogRef } from "@angular/cdk/dialog";
import { FormControl, FormGroup, ReactiveFormsModule } from "@angular/forms";
import {
  GridBlock,
  GridBlockPayload,
  FormOptions,
  FormSuggestionResponse,
} from "@project-interfaces/tv-channel";
import { TvChannelService } from "@project-services/tv-channel.service";
import {
  GridBlockService,
  GridBlockAvailableMediaCount,
} from "@project-services/grid-block.service";
import { FlwModalComponent } from "../../../ui/modal/flw-modal.component";
import { FlwSelectComponent } from "../../../ui/select/flw-select.component";
import { FlwRuleGroupComponent } from "../../../ui/rule-group/flw-rule-group.component";
import { FlwTagInputComponent } from "../../../ui/tag-input/flw-tag-input.component";
import {
  FlwSuggestionPreviewComponent,
  SuggestionChange,
} from "../../../ui/suggestion-preview/flw-suggestion-preview.component";
import { readRuleValues, ruleOptions, writeRuleValues } from "./rule-values";
import { TranslateModule, TranslateService } from "@ngx-translate/core";
import { FlwConfirmComponent } from "../../../ui/confirm/flw-confirm.component";
import { FlwDialogService } from "../../../ui/dialog.service";
import { ToastService } from "../../../ui/toast/toast.service";
import { GenerationDialogComponent } from "./generation-dialog.component";

@Component({
  standalone: true,
  imports: [
    NgIf,
    ReactiveFormsModule,
    FlwModalComponent,
    FlwSelectComponent,
    FlwRuleGroupComponent,
    FlwTagInputComponent,
    FlwSuggestionPreviewComponent,
    TranslateModule,
  ],
  template: `<flw-modal
    [title]="
      (data.block
        ? 'CHANNEL_DIALOGS.GRID.EDIT_BLOCK'
        : 'CHANNEL_DIALOGS.GRID.ADD_BLOCK'
      ) | translate
    "
    [description]="'CHANNEL_DIALOGS.GRID.DESC' | translate"
    [wide]="true"
    ><p class="tooltip-note">
      {{ "CHANNEL_DIALOGS.GRID.RULE_HINT" | translate }}
    </p>
    <div class="assistant">
      <div class="field">
        <label>{{ "CHANNEL_DIALOGS.GRID.SUGGESTION" | translate }}</label
        ><textarea
          [formControl]="prompt"
          rows="2"
          [placeholder]="'CHANNEL_DIALOGS.GRID.PROMPT' | translate"
        ></textarea>
      </div>
      <button class="btn" (click)="suggest()">
        {{ "CHANNEL_DIALOGS.GRID.SUGGEST" | translate }}
      </button>
    </div>
    <flw-suggestion-preview
      *ngIf="changes.length"
      [changes]="changes"
      (apply)="applySuggestion($event)"
      (dismiss)="changes = []"
    />
    <form [formGroup]="form" (focusout)="refreshCount()">
      <div class="field-row cols-3">
        <div class="field">
          <label>{{ "CHANNEL_DIALOGS.GRID.START" | translate }}</label
          ><input class="mono" type="time" formControlName="starts_at" />
        </div>
        <div class="field">
          <label>{{ "CHANNEL_DIALOGS.GRID.END" | translate }}</label
          ><input class="mono" type="time" formControlName="ends_at" />
        </div>
        <div class="field">
          <label>{{ "CHANNEL_DIALOGS.GRID.PRIORITY" | translate }}</label
          ><flw-select formControlName="priority" [options]="priorities" />
        </div>
      </div>
      <div class="field-row cols-4">
        <div class="field">
          <label>{{ "CHANNEL_DIALOGS.GRID.MIN_DURATION" | translate }}</label
          ><input type="number" formControlName="min_minutes" />
        </div>
        <div class="field">
          <label>{{ "CHANNEL_DIALOGS.GRID.MAX_DURATION" | translate }}</label
          ><input type="number" formControlName="max_minutes" />
        </div>
        <div class="field">
          <label>{{ "CHANNEL_DIALOGS.GRID.MIN_ITEMS" | translate }}</label
          ><input type="number" formControlName="min_items" />
        </div>
        <div class="field">
          <label>{{ "CHANNEL_DIALOGS.GRID.MAX_ITEMS" | translate }}</label
          ><input type="number" formControlName="max_items" />
        </div>
      </div>
      <div class="field">
        <label>{{ "CHANNEL_DIALOGS.GRID.POST_FILLER" | translate }}</label
        ><flw-select
          formControlName="post_filler_policy"
          [options]="policies"
        />
      </div>
      <flw-rule-group
        kind="allow"
        [label]="'CHANNEL_DIALOGS.COMMON.ALLOWED' | translate"
        ><flw-tag-input
          variant="allow"
          formControlName="allowed"
          [options]="options" /></flw-rule-group
      ><flw-rule-group
        kind="prefer"
        [label]="'CHANNEL_DIALOGS.COMMON.PREFERRED' | translate"
        ><flw-tag-input
          variant="prefer"
          formControlName="preferred"
          [options]="options" /></flw-rule-group
      ><flw-rule-group
        kind="forbid"
        [label]="'CHANNEL_DIALOGS.COMMON.FORBIDDEN' | translate"
        ><flw-tag-input
          variant="forbid"
          formControlName="forbidden"
          [options]="options"
      /></flw-rule-group>
      <p class="hint" *ngIf="availableCount !== null">
        {{
          "CHANNEL_DIALOGS.GRID.MATCHING" | translate: { count: availableCount }
        }}
      </p>
    </form>
    <div modal-footer>
      <button class="btn danger-ghost" *ngIf="data.block" (click)="remove()">
        {{ "CHANNEL_DIALOGS.GRID.DELETE_BLOCK" | translate }}</button
      ><span *ngIf="!data.block"></span>
      <div>
        <button class="btn ghost" (click)="ref.close(false)">
          {{ "CHANNEL_DIALOGS.COMMON.CANCEL" | translate }}</button
        ><button class="btn primary" (click)="save()">
          {{ "CHANNEL_DIALOGS.GRID.SAVE_BLOCK" | translate }}
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
      .assistant {
        display: grid;
        grid-template-columns: 1fr auto;
        align-items: end;
        gap: 10px;
      }
    `,
  ],
})
export class GridBlockDialogComponent {
  private empty: GridBlock = {
    id: "",
    starts_at: "18:00",
    ends_at: "19:00",
    priority: 50,
    min_items: 1,
    max_items: 1,
    min_duration_seconds_per_item: null,
    max_duration_seconds_per_item: null,
    allowed_categories: [],
    forbidden_categories: [],
    preferred_categories: [],
    allowed_natures: [],
    forbidden_natures: [],
    preferred_natures: [],
    allowed_container_kinds: [],
    forbidden_container_kinds: [],
    preferred_container_kinds: [],
    post_filler_policy: null,
    post_filler_policy_name: null,
  };
  source = this.data.block ?? { ...this.empty, ...(this.data.defaults ?? {}) };
  options = ruleOptions(this.data.formOptions, (key, params) =>
    this.translate.instant(key, params),
  );
  priorities = [80, 50, 20].map((value) => ({
    label: this.translate.instant(
      value === 80
        ? "CHANNEL_DIALOGS.GRID.HIGH"
        : value === 50
          ? "CHANNEL_DIALOGS.GRID.NORMAL"
          : "CHANNEL_DIALOGS.GRID.LOW",
    ),
    value,
  }));
  policies = [
    {
      label: this.translate.instant("CHANNEL_DIALOGS.GRID.NONE"),
      value: null,
    },
    ...this.data.formOptions.filler_policies.map((p) => ({
      label: `${p.name} (${p.duration_seconds}s)`,
      value: p.id,
    })),
  ];
  prompt = new FormControl("", { nonNullable: true });
  changes: SuggestionChange[] = [];
  suggested: Record<string, unknown> = {};
  availableCount: number | null = null;
  form = new FormGroup({
    starts_at: new FormControl(this.source.starts_at.slice(0, 5), {
      nonNullable: true,
    }),
    ends_at: new FormControl(this.source.ends_at.slice(0, 5), {
      nonNullable: true,
    }),
    priority: new FormControl(this.source.priority, { nonNullable: true }),
    min_minutes: new FormControl(
      this.source.min_duration_seconds_per_item
        ? Math.round(this.source.min_duration_seconds_per_item / 60)
        : null,
    ),
    max_minutes: new FormControl(
      this.source.max_duration_seconds_per_item
        ? Math.round(this.source.max_duration_seconds_per_item / 60)
        : null,
    ),
    min_items: new FormControl(this.source.min_items, { nonNullable: true }),
    max_items: new FormControl(this.source.max_items, { nonNullable: true }),
    post_filler_policy: new FormControl(this.source.post_filler_policy),
    allowed: new FormControl(readRuleValues(this.source, "allowed"), {
      nonNullable: true,
    }),
    preferred: new FormControl(readRuleValues(this.source, "preferred"), {
      nonNullable: true,
    }),
    forbidden: new FormControl(readRuleValues(this.source, "forbidden"), {
      nonNullable: true,
    }),
  });
  constructor(
    private channels: TvChannelService,
    private translate: TranslateService,
    private blocks: GridBlockService,
    private dialogs: FlwDialogService,
    private toast: ToastService,
    public ref: DialogRef<boolean>,
    @Inject(DIALOG_DATA)
    public data: {
      channelId: string | number;
      channelName: string;
      gridLayoutId: string | number;
      block: GridBlock | null;
      defaults?: { starts_at: string; ends_at: string };
      formOptions: FormOptions;
    },
  ) {
    if (data.block) this.refreshCount();
  }
  payload(): GridBlockPayload {
    const v = this.form.getRawValue();
    const payload: any = {
      grid_layout: this.data.gridLayoutId,
      starts_at: v.starts_at,
      ends_at: v.ends_at,
      priority: v.priority,
      min_items: v.min_items,
      max_items: v.max_items,
      min_duration_seconds_per_item: v.min_minutes
        ? Number(v.min_minutes) * 60
        : null,
      max_duration_seconds_per_item: v.max_minutes
        ? Number(v.max_minutes) * 60
        : null,
      post_filler_policy: v.post_filler_policy,
    };
    writeRuleValues(payload, "allowed", v.allowed);
    writeRuleValues(payload, "preferred", v.preferred);
    writeRuleValues(payload, "forbidden", v.forbidden);
    return payload;
  }
  suggest() {
    this.channels
      .suggestForm(this.data.channelId, {
        form_kind: "grid_block",
        user_context: this.prompt.value,
        current_values: this.payload(),
        grid_block_id: this.data.block?.id,
      })
      .subscribe((r) => {
        if (!r.isOk) return;
        this.suggested = (r.body as FormSuggestionResponse).values;
        const current = this.payload() as any;
        this.changes = Object.entries(this.suggested)
          .filter(
            ([key, value]) =>
              JSON.stringify(current[key]) !== JSON.stringify(value),
          )
          .map(([key, value]) => ({
            key,
            label: key.replaceAll("_", " "),
            kind: "replace",
            from: current[key],
            to: value,
          }));
      });
  }
  applySuggestion(changes: SuggestionChange[]) {
    const patch: any = {};
    for (const change of changes) patch[change.key] = change.to;
    const scalar: any = {
      starts_at: "starts_at",
      ends_at: "ends_at",
      priority: "priority",
      min_items: "min_items",
      max_items: "max_items",
      post_filler_policy: "post_filler_policy",
    };
    for (const [key, control] of Object.entries(scalar))
      if (key in patch) this.form.get(control as string)?.setValue(patch[key]);
    if ("min_duration_seconds_per_item" in patch)
      this.form.controls.min_minutes.setValue(
        this.secondsToMinutes(patch["min_duration_seconds_per_item"]),
      );
    if ("max_duration_seconds_per_item" in patch)
      this.form.controls.max_minutes.setValue(
        this.secondsToMinutes(patch["max_duration_seconds_per_item"]),
      );
    for (const level of ["allowed", "preferred", "forbidden"] as const) {
      const combined = [
        ...(
          patch[`${level}_categories`] ??
          (this.payload() as any)[`${level}_categories`]
        ).map((v: any) => `category:${v}`),
        ...(
          patch[`${level}_natures`] ??
          (this.payload() as any)[`${level}_natures`]
        ).map((v: any) => `nature:${v}`),
        ...(
          patch[`${level}_container_kinds`] ??
          (this.payload() as any)[`${level}_container_kinds`]
        ).map((v: any) => `kind:${v}`),
      ];
      this.form.controls[level].setValue(combined);
    }
    this.changes = [];
    this.refreshCount();
  }
  save() {
    const request = this.data.block
      ? this.blocks.update(this.data.block.id, this.payload())
      : this.blocks.create(this.payload());
    request.subscribe((r) => {
      if (!r.isOk) return;
      this.toast.show(this.translate.instant("CHANNEL_DIALOGS.GRID.SAVED"), {
        action: this.translate.instant("CHANNEL_DIALOGS.GRID.REGENERATE"),
        duration: 10000,
        onAction: () =>
          this.dialogs.open(GenerationDialogComponent, {
            data: {
              channelId: this.data.channelId,
              channelName: this.data.channelName,
              kind: "playout",
            },
          }),
      });
      this.ref.close(true);
    });
  }
  remove() {
    if (!this.data.block) return;
    this.dialogs
      .open(FlwConfirmComponent, {
        data: {
          title: this.translate.instant("CHANNEL_DIALOGS.GRID.DELETE_BLOCK"),
          message: this.translate.instant(
            "CHANNEL_DIALOGS.GRID.CONFIRM_DELETE",
          ),
          confirmLabel: this.translate.instant("COMMON.DELETE"),
        },
      })
      .closed.subscribe((confirmed) => {
        if (!confirmed || !this.data.block) return;
        this.blocks.delete(this.data.block.id).subscribe((r) => {
          if (r.isOk) this.ref.close(true);
        });
      });
  }
  refreshCount() {
    if (this.data.block)
      this.blocks
        .getAvailableMediaCount(this.data.block.id, this.payload())
        .subscribe((r) => {
          if (r.isOk)
            this.availableCount = (
              r.body as GridBlockAvailableMediaCount
            ).count;
        });
  }

  private secondsToMinutes(value: unknown): number | null {
    if (value === null || value === undefined || value === "") return null;
    const seconds = Number(value);
    return Number.isFinite(seconds) ? Math.round(seconds / 60) : null;
  }
}
