import { Component, Inject } from "@angular/core";
import { DIALOG_DATA, DialogRef } from "@angular/cdk/dialog";
import { FormControl, FormGroup, ReactiveFormsModule } from "@angular/forms";
import { EditorialLineData, FormOptions } from "@project-interfaces/tv-channel";
import { TvChannelService } from "@project-services/tv-channel.service";
import { FlwModalComponent } from "../../../ui/modal/flw-modal.component";
import { FlwSwitchComponent } from "../../../ui/switch/flw-switch.component";
import { FlwRuleGroupComponent } from "../../../ui/rule-group/flw-rule-group.component";
import { FlwTagInputComponent } from "../../../ui/tag-input/flw-tag-input.component";
import { readRuleValues, ruleOptions, writeRuleValues } from "./rule-values";

@Component({
  standalone: true,
  imports: [
    ReactiveFormsModule,
    FlwModalComponent,
    FlwSwitchComponent,
    FlwRuleGroupComponent,
    FlwTagInputComponent,
  ],
  template: `<flw-modal title="Modifier la ligne éditoriale" [wide]="true"
    ><form [formGroup]="form">
      <div class="field-row cols-2">
        <div class="field">
          <label>Début de diffusion</label
          ><input class="mono" type="time" formControlName="start_at" />
        </div>
        <div class="field">
          <label>Fin de diffusion</label
          ><input class="mono" type="time" formControlName="end_at" />
        </div>
      </div>
      <flw-switch
        formControlName="allow_filler"
        label="Autoriser le filler entre les titres"
      /><flw-rule-group kind="allow" label="Autorisé"
        ><flw-tag-input
          variant="allow"
          formControlName="allowed"
          [options]="options" /></flw-rule-group
      ><flw-rule-group kind="prefer" label="Préféré"
        ><flw-tag-input
          variant="prefer"
          formControlName="preferred"
          [options]="options" /></flw-rule-group
      ><flw-rule-group kind="forbid" label="Interdit"
        ><flw-tag-input
          variant="forbid"
          formControlName="forbidden"
          [options]="options"
      /></flw-rule-group>
    </form>
    <div modal-footer>
      <button class="btn ghost" (click)="ref.close(false)">Annuler</button
      ><button class="btn primary" (click)="save()">Enregistrer</button>
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
export class EditorialLineDialogComponent {
  options = ruleOptions(this.data.formOptions);
  form = new FormGroup({
    start_at: new FormControl(this.data.line.start_at.slice(0, 5), {
      nonNullable: true,
    }),
    end_at: new FormControl(this.data.line.end_at.slice(0, 5), {
      nonNullable: true,
    }),
    allow_filler: new FormControl(this.data.line.allow_filler, {
      nonNullable: true,
    }),
    allowed: new FormControl(readRuleValues(this.data.line, "allowed"), {
      nonNullable: true,
    }),
    preferred: new FormControl(readRuleValues(this.data.line, "preferred"), {
      nonNullable: true,
    }),
    forbidden: new FormControl(readRuleValues(this.data.line, "forbidden"), {
      nonNullable: true,
    }),
  });
  constructor(
    private service: TvChannelService,
    public ref: DialogRef<boolean>,
    @Inject(DIALOG_DATA)
    public data: {
      channelId: string | number;
      line: EditorialLineData;
      formOptions: FormOptions;
    },
  ) {}
  save() {
    const value = this.form.getRawValue();
    const payload: Record<string, unknown> = {
      start_at: value.start_at,
      end_at: value.end_at,
      allow_filler: value.allow_filler,
    };
    writeRuleValues(payload, "allowed", value.allowed);
    writeRuleValues(payload, "preferred", value.preferred);
    writeRuleValues(payload, "forbidden", value.forbidden);
    this.service
      .updateEditorialLine(this.data.channelId, payload)
      .subscribe((r) => {
        if (r.isOk) this.ref.close(true);
      });
  }
}
