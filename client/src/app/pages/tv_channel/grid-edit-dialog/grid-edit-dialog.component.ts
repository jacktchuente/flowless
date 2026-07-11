import {Component, Inject} from '@angular/core';
import {FormGroup, ReactiveFormsModule} from '@angular/forms';
import {NgIf} from '@angular/common';
import {MAT_DIALOG_DATA, MatDialogModule, MatDialogRef} from '@angular/material/dialog';
import {MatButtonModule} from '@angular/material/button';
import {MatProgressSpinnerModule} from '@angular/material/progress-spinner';
import {FormlyFieldConfig, FormlyModule} from '@ngx-formly/core';
import {TranslateModule, TranslateService} from '@ngx-translate/core';
import {FormOptions, FormSuggestionResponse, GridPayload} from '@project-interfaces/tv-channel';
import {TvChannelService} from '@project-services/tv-channel.service';
import {DialogContainer1Component} from '@project-templates/dialog-container1/dialog-container1.component';
import {SuggestionPanelComponent} from '@project-templates/suggestion-panel/suggestion-panel.component';

@Component({
  selector: 'app-grid-edit-dialog',
  standalone: true,
  imports: [
    ReactiveFormsModule,
    NgIf,
    MatDialogModule,
    MatButtonModule,
    MatProgressSpinnerModule,
    FormlyModule,
    TranslateModule,
    DialogContainer1Component,
    SuggestionPanelComponent,
  ],
  templateUrl: './grid-edit-dialog.component.html',
})
export class GridEditDialogComponent {
  form = new FormGroup({})
  model: GridPayload
  fields: FormlyFieldConfig[]
  isSubmitting = false
  isSuggesting = false
  error: string | null = null

  constructor(
    private service: TvChannelService,
    private ref: MatDialogRef<GridEditDialogComponent>,
    private translate: TranslateService,
    @Inject(MAT_DIALOG_DATA) public data: {
      channelId: string | number,
      postFillerPolicy: string | number | null,
      formOptions: FormOptions,
    },
  ) {
    this.model = {post_filler_policy: data.postFillerPolicy}
    this.fields = [{
      key: 'post_filler_policy',
      type: 'select',
      props: {
        label: this.translate.instant('MANUAL_EDIT.FILLER_POLICY'),
        options: [
          {label: this.translate.instant('MANUAL_EDIT.NONE'), value: null},
          ...data.formOptions.filler_policies.map((policy) => ({
            label: `${policy.name} (${policy.duration_seconds}s)`,
            value: policy.id,
          })),
        ],
      },
    }]
  }

  suggest(context: string) {
    this.isSuggesting = true
    this.error = null
    this.service.suggestForm(this.data.channelId, {
      form_kind: 'grid',
      user_context: context,
      current_values: {...this.model},
    }).subscribe((response) => {
      this.isSuggesting = false
      if (!response.isOk) {
        this.error = this.detail(response.body)
        return
      }
      const values = (response.body as FormSuggestionResponse).values
      Object.assign(this.model, values)
      this.form.patchValue(values)
    })
  }

  save() {
    if (this.form.invalid || this.isSubmitting) {
      this.form.markAllAsTouched()
      return
    }
    this.isSubmitting = true
    this.service.updateGrid(this.data.channelId, this.model).subscribe((response) => {
      this.isSubmitting = false
      if (!response.isOk) {
        this.error = this.detail(response.body)
        return
      }
      this.ref.close({saved: true})
    })
  }

  private detail(value: any) {
    return value?.error?.detail
      ?? (value?.error ? JSON.stringify(value.error) : this.translate.instant('MANUAL_EDIT.SAVE_FAILED'))
  }
}
