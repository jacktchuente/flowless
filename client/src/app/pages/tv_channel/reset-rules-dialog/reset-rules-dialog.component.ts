import {Component, Inject} from '@angular/core';
import {FormsModule} from "@angular/forms";
import {NgFor, NgIf} from "@angular/common";
import {MAT_DIALOG_DATA, MatDialogModule, MatDialogRef} from "@angular/material/dialog";
import {MatButtonModule} from "@angular/material/button";
import {MatCheckboxModule} from "@angular/material/checkbox";
import {MatProgressSpinnerModule} from "@angular/material/progress-spinner";
import {DialogContainer1Component} from "@project-templates/dialog-container1/dialog-container1.component";
import {
  TvChannelResetRulesPayload,
  TvChannelService
} from "@project-services/tv-channel.service";
import {NotificationService} from "@project-shared/services/notification.service";

type RuleTypeOption = TvChannelResetRulesPayload['types'][number]
type RuleLevelOption = TvChannelResetRulesPayload['levels'][number]

@Component({
  selector: 'app-reset-rules-dialog',
  standalone: true,
  imports: [
    DialogContainer1Component,
    FormsModule,
    MatButtonModule,
    MatCheckboxModule,
    MatDialogModule,
    MatProgressSpinnerModule,
    NgFor,
    NgIf,
  ],
  templateUrl: './reset-rules-dialog.component.html',
  styleUrl: './reset-rules-dialog.component.css'
})
export class ResetRulesDialogComponent {
  readonly selectedTypes = new Set<RuleTypeOption>(['nature', 'kind', 'category'])
  readonly selectedLevels = new Set<RuleLevelOption>(['allowed', 'forbidden'])
  readonly typeOptions: Array<{value: RuleTypeOption, label: string}> = [
    {value: 'category', label: 'Categories'},
    {value: 'nature', label: 'Natures'},
    {value: 'kind', label: 'Types de conteneur'},
  ]
  readonly levelOptions: Array<{value: RuleLevelOption, label: string}> = [
    {value: 'allowed', label: 'Regles autorisees'},
    {value: 'forbidden', label: 'Regles interdites'},
  ]

  isSubmitting = false
  errorMessage: string | null = null

  constructor(
    private tvChannelService: TvChannelService,
    private notificationService: NotificationService,
    private dialogRef: MatDialogRef<ResetRulesDialogComponent>,
    @Inject(MAT_DIALOG_DATA) public data: {
      channelId: string | number,
      channelName: string,
    }
  ) {}

  get canSubmit(): boolean {
    return !this.isSubmitting && this.selectedTypes.size > 0 && this.selectedLevels.size > 0
  }

  toggleType(value: RuleTypeOption, checked: boolean) {
    if (checked) {
      this.selectedTypes.add(value)
      return
    }
    this.selectedTypes.delete(value)
  }

  toggleLevel(value: RuleLevelOption, checked: boolean) {
    if (checked) {
      this.selectedLevels.add(value)
      return
    }
    this.selectedLevels.delete(value)
  }

  isTypeSelected(value: RuleTypeOption): boolean {
    return this.selectedTypes.has(value)
  }

  isLevelSelected(value: RuleLevelOption): boolean {
    return this.selectedLevels.has(value)
  }

  save() {
    if (!this.canSubmit) {
      this.errorMessage = "Selectionnez au moins un type et un niveau."
      return
    }

    this.errorMessage = null
    this.isSubmitting = true

    const payload: TvChannelResetRulesPayload = {
      types: Array.from(this.selectedTypes),
      levels: Array.from(this.selectedLevels),
    }

    this.tvChannelService.resetRules(this.data.channelId, payload).subscribe((response) => {
      this.isSubmitting = false
      if (!response.isOk) {
        this.errorMessage = "Reinitialisation impossible."
        this.notificationService.notify(this.errorMessage)
        return
      }
      this.dialogRef.close(true)
    })
  }
}
