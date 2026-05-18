import {Component, Inject} from '@angular/core';
import {ReactiveFormsModule} from "@angular/forms";
import {MAT_DIALOG_DATA, MatDialogModule, MatDialogRef} from "@angular/material/dialog";
import {MatButtonModule} from "@angular/material/button";
import {MatProgressSpinnerModule} from "@angular/material/progress-spinner";
import {FormlyFieldConfig, FormlyModule} from "@ngx-formly/core";
import {FormGroup} from "@angular/forms";
import {MediaSource, MediaSourcePayload} from "@project-interfaces/media-source";
import {MediaSourceService} from "@project-services/media-source.service";
import {DialogContainer1Component} from "@project-templates/dialog-container1/dialog-container1.component";
import {NotificationService} from "@project-shared/services/notification.service";
import {NgIf} from "@angular/common";

@Component({
  selector: 'app-media-source-dialog',
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
  templateUrl: './media-source-dialog.component.html',
  styleUrl: './media-source-dialog.component.css'
})
export class MediaSourceDialogComponent {
  readonly form = new FormGroup({})
  readonly model: MediaSourcePayload
  readonly fields: FormlyFieldConfig[] = [
    {
      key: 'name',
      type: 'input',
      props: {
        label: 'Nom',
        required: true,
        placeholder: 'Jellyfin principal',
      }
    },
    {
      fieldGroupClassName: 'credentials-grid',
      fieldGroup: [
        {
          key: 'credentials.application_url',
          type: 'input',
          props: {
            label: 'URL Jellyfin',
            required: true,
            placeholder: 'https://jellyfin.example.com',
          }
        },
        {
          key: 'credentials.username',
          type: 'input',
          props: {
            label: 'Utilisateur',
            required: true,
          }
        },
        {
          key: 'credentials.password',
          type: 'input',
          props: {
            label: 'Mot de passe',
            type: 'password',
            required: true,
          }
        }
      ]
    }
  ]

  isSubmitting = false
  errorMessage: string | null = null

  constructor(
    private mediaSourceService: MediaSourceService,
    private notificationService: NotificationService,
    private dialogRef: MatDialogRef<MediaSourceDialogComponent>,
    @Inject(MAT_DIALOG_DATA) public data: { source?: MediaSource }
  ) {
    this.model = {
      name: data.source?.name ?? '',
      source_type: data.source?.source_type ?? 1,
      credentials: {
        application_url: data.source?.credentials?.application_url ?? '',
        username: data.source?.credentials?.username ?? '',
        password: data.source?.credentials?.password ?? '',
      }
    }
  }

  save() {
    if (this.form.invalid || this.isSubmitting) {
      this.form.markAllAsTouched()
      return
    }

    this.isSubmitting = true
    this.errorMessage = null

    this.mediaSourceService.verifyCredentials(this.model).subscribe((verifyResponse) => {
      if (!verifyResponse.isOk) {
        this.isSubmitting = false
        this.errorMessage = this.extractErrorMessage(verifyResponse.body)
        this.notificationService.notify(this.errorMessage)
        return
      }

      const request = this.data.source
        ? this.mediaSourceService.patchObject(this.data.source.id.toString(), this.model)
        : this.mediaSourceService.createObject(this.model)

      request.subscribe((response) => {
        this.isSubmitting = false
        if (!response.isOk) {
          this.errorMessage = this.extractErrorMessage(response.body)
          this.notificationService.notify(this.errorMessage)
          return
        }

        this.dialogRef.close(true)
      })
    })
  }

  private extractErrorMessage(error: unknown): string {
    const httpError = error as { error?: { credentials?: string[], detail?: string }, message?: string }
    if (httpError?.error?.credentials?.length) {
      return httpError.error.credentials[0]
    }
    if (httpError?.error?.detail) {
      return httpError.error.detail
    }
    if (httpError?.message) {
      return httpError.message
    }
    return "Une erreur est survenue lors de la verification de la source."
  }
}
