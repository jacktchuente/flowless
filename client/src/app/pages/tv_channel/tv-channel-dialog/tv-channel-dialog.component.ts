import {Component, Inject} from '@angular/core';
import {AbstractControl, FormGroup, ReactiveFormsModule} from "@angular/forms";
import {NgFor, NgIf} from "@angular/common";
import {MAT_DIALOG_DATA, MatDialogModule, MatDialogRef} from "@angular/material/dialog";
import {MatButtonModule} from "@angular/material/button";
import {MatIconModule} from "@angular/material/icon";
import {MatProgressSpinnerModule} from "@angular/material/progress-spinner";
import {FormlyFieldConfig, FormlyModule} from "@ngx-formly/core";
import {TranslateModule} from "@ngx-translate/core";
import {Catalog} from "@project-interfaces/catalog";
import {TvChannel, TvChannelPayload} from "@project-interfaces/tv-channel";
import {NotificationService} from "@project-shared/services/notification.service";
import {DialogContainer1Component} from "@project-templates/dialog-container1/dialog-container1.component";
import {TvChannelNameSuggestionResponse, TvChannelService} from "@project-services/tv-channel.service";

@Component({
  selector: 'app-tv-channel-dialog',
  standalone: true,
  imports: [
    DialogContainer1Component,
    FormlyModule,
    MatButtonModule,
    MatDialogModule,
    MatIconModule,
    MatProgressSpinnerModule,
    NgFor,
    NgIf,
    ReactiveFormsModule,
    TranslateModule
  ],
  templateUrl: './tv-channel-dialog.component.html',
  styleUrl: './tv-channel-dialog.component.css'
})
export class TvChannelDialogComponent {
  readonly form = new FormGroup({})
  readonly model: TvChannelPayload
  readonly fields: FormlyFieldConfig[]
  readonly editorialFields: Array<{label: string, value: string | number | null}>

  isSubmitting = false
  isSuggestingName = false
  errorMessage: string | null = null

  constructor(
    private tvChannelService: TvChannelService,
    private notificationService: NotificationService,
    private dialogRef: MatDialogRef<TvChannelDialogComponent>,
    @Inject(MAT_DIALOG_DATA) public data: {
      channel?: TvChannel,
      selectedCatalogId?: string | number | null,
      catalogs: Catalog[]
    }
  ) {
    this.model = {
      name: data.channel?.name ?? '',
      description: data.channel?.description ?? '',
      specification: data.channel?.specification ?? '',
      catalog: data.channel?.catalog ?? data.selectedCatalogId ?? '',
    }
    this.fields = [
      {
        key: 'name',
        type: 'input',
        props: {
          label: 'Nom',
          required: true,
        }
      },
      {
        key: 'description',
        type: 'textarea',
        props: {
          label: 'Description',
          rows: 4,
        }
      },
      {
        key: 'specification',
        type: 'textarea',
        props: {
          label: 'Specification',
          rows: 5,
        }
      },
      {
        key: 'catalog',
        type: 'select',
        props: {
          label: 'Catalogue',
          required: true,
          options: data.catalogs.map((catalog) => ({
            label: catalog.name,
            value: catalog.id,
          })),
        }
      }
    ]
    const editorial = data.channel?.editorial_line_data
    this.editorialFields = editorial ? [
      {label: 'Allowed categories', value: this.stringifyValue(editorial.allowed_categories)},
      {label: 'Forbidden categories', value: this.stringifyValue(editorial.forbidden_categories)},
      {label: 'Preferred categories', value: this.stringifyValue(editorial.preferred_categories)},
      {label: 'Allowed natures', value: this.stringifyValue(editorial.allowed_natures)},
      {label: 'Forbidden natures', value: this.stringifyValue(editorial.forbidden_natures)},
      {label: 'Preferred natures', value: this.stringifyValue(editorial.preferred_natures)},
      {label: 'Allowed container kinds', value: this.stringifyValue(editorial.allowed_container_kinds)},
      {label: 'Forbidden container kinds', value: this.stringifyValue(editorial.forbidden_container_kinds)},
      {label: 'Preferred container kinds', value: this.stringifyValue(editorial.preferred_container_kinds)},
      {label: 'Start', value: editorial.start_at},
      {label: 'End', value: editorial.end_at},
      {label: 'Allow filler', value: editorial.allow_filler ? 'Oui' : 'Non'},
    ] : []
  }

  suggestName() {
    if (!this.data.channel || this.isSuggestingName || this.isSubmitting) {
      return
    }
    this.isSuggestingName = true
    this.tvChannelService.suggestName(this.data.channel.id).subscribe((response) => {
      this.isSuggestingName = false
      if (!response.isOk) {
        this.notificationService.notify("TV_CHANNEL_DIALOG.NOTIFY_SUGGEST_NAME_FAILED")
        return
      }
      const body = response.body as TvChannelNameSuggestionResponse
      const name = body?.name?.trim()
      if (!name) {
        this.notificationService.notify("TV_CHANNEL_DIALOG.NOTIFY_SUGGEST_NAME_FAILED")
        return
      }
      const nameControl = this.form.get('name') as AbstractControl<string> | null
      nameControl?.setValue(name)
      nameControl?.markAsDirty()
    })
  }

  save() {
    if (this.form.invalid || this.isSubmitting) {
      this.form.markAllAsTouched()
      return
    }
    this.isSubmitting = true

    const request = this.data.channel
      ? this.tvChannelService.patchObject(this.data.channel.id.toString(), this.model)
      : this.tvChannelService.createObject(this.model)

    request.subscribe((response) => {
      this.isSubmitting = false
      if (!response.isOk) {
        this.errorMessage = "Enregistrement impossible."
        this.notificationService.notify(this.errorMessage)
        return
      }
      this.dialogRef.close(true)
    })
  }

  private stringifyValue(value: unknown): string | null {
    if (value === null || value === undefined) {
      return null
    }
    if (Array.isArray(value)) {
      return value.length ? value.join(', ') : null
    }
    if (typeof value === 'object') {
      return JSON.stringify(value, null, 2)
    }
    return String(value)
  }
}
