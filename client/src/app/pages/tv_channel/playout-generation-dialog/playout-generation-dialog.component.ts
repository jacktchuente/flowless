import {Component, Inject} from '@angular/core';
import {FormGroup, ReactiveFormsModule} from "@angular/forms";
import {NgIf} from "@angular/common";
import {MAT_DIALOG_DATA, MatDialogModule, MatDialogRef} from "@angular/material/dialog";
import {MatButtonModule} from "@angular/material/button";
import {MatProgressSpinnerModule} from "@angular/material/progress-spinner";
import {FormlyFieldConfig, FormlyModule} from "@ngx-formly/core";
import {TvPlayoutGenerationPayload, TvChannelService} from "@project-services/tv-channel.service";
import {NotificationService} from "@project-shared/services/notification.service";
import {DialogContainer1Component} from "@project-templates/dialog-container1/dialog-container1.component";

@Component({
  selector: 'app-playout-generation-dialog',
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
  templateUrl: './playout-generation-dialog.component.html',
  styleUrl: './playout-generation-dialog.component.css'
})
export class PlayoutGenerationDialogComponent {
  readonly form = new FormGroup({})
  readonly model: TvPlayoutGenerationPayload = {
    days: 1,
    reset: false,
  }
  readonly fields: FormlyFieldConfig[] = [
    {
      key: 'days',
      type: 'input',
      props: {
        type: 'number',
        label: 'Nombre de jours',
        required: true,
        min: 1,
      }
    },
    {
      key: 'reset',
      type: 'checkbox',
      props: {
        label: 'Repartir de zero avec un nouveau playout actif',
      }
    },
  ]

  isSubmitting = false
  errorMessage: string | null = null

  constructor(
    private tvChannelService: TvChannelService,
    private notificationService: NotificationService,
    private dialogRef: MatDialogRef<PlayoutGenerationDialogComponent>,
    @Inject(MAT_DIALOG_DATA) public data: {
      channelId?: string | number,
    }
  ) {}

  get title(): string {
    return 'Generer le playout'
  }

  save() {
    if (this.form.invalid || this.isSubmitting) {
      this.form.markAllAsTouched()
      return
    }
    this.isSubmitting = true

    const request = this.tvChannelService.generatePlayout(this.data.channelId!, this.model)

    request.subscribe((response) => {
      this.isSubmitting = false
      if (!response.isOk) {
        this.errorMessage = "Generation du playout impossible."
        this.notificationService.notify(this.errorMessage)
        return
      }
      this.dialogRef.close(true)
    })
  }
}
