import {Component, Inject} from '@angular/core';
import {FormGroup, ReactiveFormsModule} from "@angular/forms";
import {NgIf} from "@angular/common";
import {MAT_DIALOG_DATA, MatDialogModule, MatDialogRef} from "@angular/material/dialog";
import {MatButtonModule} from "@angular/material/button";
import {MatProgressSpinnerModule} from "@angular/material/progress-spinner";
import {FormlyFieldConfig, FormlyModule} from "@ngx-formly/core";
import {TvChannelBlueprintPayload, TvChannelService} from "@project-services/tv-channel.service";
import {NotificationService} from "@project-shared/services/notification.service";
import {DialogContainer1Component} from "@project-templates/dialog-container1/dialog-container1.component";

@Component({
  selector: 'app-blueprint-generation-dialog',
  standalone: true,
  imports: [
    DialogContainer1Component,
    FormlyModule,
    MatButtonModule,
    MatDialogModule,
    MatProgressSpinnerModule,
    NgIf,
    ReactiveFormsModule
  ],
  templateUrl: './blueprint-generation-dialog.component.html',
  styleUrl: './blueprint-generation-dialog.component.css'
})
export class BlueprintGenerationDialogComponent {
  readonly form = new FormGroup({})
  readonly model: TvChannelBlueprintPayload = {
    reboot: false,
    grid_generation_mode: 'preset_and_llm',
    grid_only: true,
  }
  readonly fields: FormlyFieldConfig[] = [
    {
      key: 'grid_only',
      type: 'checkbox',
      props: {
        label: 'Regenerer uniquement la grille',
        description: 'Si active, la ligne editoriale existante est conservee.',
      }
    },
    {
      key: 'grid_generation_mode',
      type: 'radio',
      props: {
        label: 'Mode de generation de la grille',
        required: true,
        options: [
          {
            value: 'preset_and_llm',
            label: 'LLM + presets',
          },
          {
            value: 'random',
            label: 'LLM + aleatoire calcule',
          },
          {
            value: 'full_llm',
            label: 'LLM 100%',
          }
        ],
        description: 'Choisit comment la grille est construite a partir de la ligne editoriale.',
      }
    },
    {
      key: 'reboot',
      type: 'checkbox',
      props: {
        label: 'Forcer la regeneration meme si une ligne edito ou une grille existent deja',
      }
    }
  ]

  isSubmitting = false
  errorMessage: string | null = null

  constructor(
    private tvChannelService: TvChannelService,
    private notificationService: NotificationService,
    private dialogRef: MatDialogRef<BlueprintGenerationDialogComponent>,
    @Inject(MAT_DIALOG_DATA) public data: {
      channelId?: string | number,
      channelName?: string,
    }
  ) {}

  get title(): string {
    return `Generation auto de ${this.data.channelName}`
  }

  save() {
    if (this.form.invalid || this.isSubmitting) {
      this.form.markAllAsTouched()
      return
    }
    this.isSubmitting = true

    const request = this.tvChannelService.generateBlueprint(this.data.channelId!, this.model)

    request.subscribe((response) => {
      this.isSubmitting = false
      if (!response.isOk) {
        this.errorMessage = "Generation impossible."
        this.notificationService.notify(this.errorMessage)
        return
      }
      this.dialogRef.close(true)
    })
  }
}
