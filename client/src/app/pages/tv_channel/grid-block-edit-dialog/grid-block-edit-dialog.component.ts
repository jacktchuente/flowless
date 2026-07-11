import {Component, Inject} from '@angular/core';
import {FormGroup, ReactiveFormsModule} from '@angular/forms';
import {NgIf} from '@angular/common';
import {MAT_DIALOG_DATA, MatDialogModule, MatDialogRef} from '@angular/material/dialog';
import {MatButtonModule} from '@angular/material/button';
import {MatProgressSpinnerModule} from '@angular/material/progress-spinner';
import {FormlyFieldConfig, FormlyModule} from '@ngx-formly/core';
import {TranslateModule, TranslateService} from '@ngx-translate/core';
import {FormOptions, FormSuggestionResponse, GridBlock, GridBlockPayload} from '@project-interfaces/tv-channel';
import {GridBlockService} from '@project-services/grid-block.service';
import {TvChannelService} from '@project-services/tv-channel.service';
import {DialogContainer1Component} from '@project-templates/dialog-container1/dialog-container1.component';
import {SuggestionPanelComponent} from '@project-templates/suggestion-panel/suggestion-panel.component';

@Component({
  selector: 'app-grid-block-edit-dialog',
  standalone: true,
  imports: [ReactiveFormsModule, NgIf, MatDialogModule, MatButtonModule, MatProgressSpinnerModule,
    FormlyModule, TranslateModule, DialogContainer1Component, SuggestionPanelComponent],
  templateUrl: './grid-block-edit-dialog.component.html',
  styleUrl: './grid-block-edit-dialog.component.css',
})
export class GridBlockEditDialogComponent {
  form = new FormGroup({})
  model: GridBlockPayload
  fields: FormlyFieldConfig[]
  isSubmitting = false
  isSuggesting = false
  error: string | null = null

  constructor(
    private blocks: GridBlockService,
    private channels: TvChannelService,
    private ref: MatDialogRef<GridBlockEditDialogComponent>,
    private translate: TranslateService,
    @Inject(MAT_DIALOG_DATA) public data: {channelId: string | number, gridLayoutId: string | number, block: GridBlock | null, formOptions: FormOptions},
  ) {
    this.model = {...this.empty(), ...(data.block ?? {}), grid_layout: data.gridLayoutId}
    const multi = (key: string, labelKey: string, options: any[]): FormlyFieldConfig => ({
      key, type: 'select', props: {label: this.translate.instant(labelKey), multiple: true, options},
    })
    const categories = data.formOptions.categories.map((value) => ({label: value, value}))
    const field = (key: string, labelKey: string, props: object = {}): FormlyFieldConfig => ({
      key, type: 'input', props: {label: this.translate.instant(labelKey), ...props},
    })
    this.fields = [
      {fieldGroupClassName: 'compact-row', fieldGroup: [field('starts_at', 'MANUAL_EDIT.START', {type: 'time', required: true}), field('ends_at', 'MANUAL_EDIT.END', {type: 'time', required: true}), field('priority', 'MANUAL_EDIT.PRIORITY', {type: 'number', min: 0, max: 100, required: true})]},
      {fieldGroupClassName: 'compact-row', fieldGroup: [field('min_items', 'MANUAL_EDIT.MIN_ITEMS', {type: 'number', min: 1, max: 3, required: true}), field('max_items', 'MANUAL_EDIT.MAX_ITEMS', {type: 'number', min: 1, max: 3, required: true}), field('min_duration_seconds_per_item', 'MANUAL_EDIT.MIN_DURATION', {type: 'number', min: 1}), field('max_duration_seconds_per_item', 'MANUAL_EDIT.MAX_DURATION', {type: 'number', min: 1})]},
      multi('allowed_categories', 'MANUAL_EDIT.ALLOWED_CATEGORIES', categories),
      multi('forbidden_categories', 'MANUAL_EDIT.FORBIDDEN_CATEGORIES', categories),
      multi('preferred_categories', 'MANUAL_EDIT.PREFERRED_CATEGORIES', categories),
      multi('allowed_natures', 'MANUAL_EDIT.ALLOWED_NATURES', data.formOptions.natures),
      multi('forbidden_natures', 'MANUAL_EDIT.FORBIDDEN_NATURES', data.formOptions.natures),
      multi('preferred_natures', 'MANUAL_EDIT.PREFERRED_NATURES', data.formOptions.natures),
      multi('allowed_container_kinds', 'MANUAL_EDIT.ALLOWED_KINDS', data.formOptions.container_kinds),
      multi('forbidden_container_kinds', 'MANUAL_EDIT.FORBIDDEN_KINDS', data.formOptions.container_kinds),
      multi('preferred_container_kinds', 'MANUAL_EDIT.PREFERRED_KINDS', data.formOptions.container_kinds),
      {key: 'post_filler_policy', type: 'select', props: {label: this.translate.instant('MANUAL_EDIT.POST_FILLER_POLICY'), options: [{label: this.translate.instant('MANUAL_EDIT.NONE'), value: null}, ...data.formOptions.filler_policies.map((policy) => ({label: `${policy.name} (${policy.duration_seconds}s)`, value: policy.id}))]}},
    ]
  }

  suggest(context: string) {
    this.isSuggesting = true
    this.error = null
    const {grid_layout, ...values} = this.model
    this.channels.suggestForm(this.data.channelId, {form_kind: 'grid_block', user_context: context, current_values: values, ...(this.data.block ? {grid_block_id: this.data.block.id} : {})}).subscribe((response) => {
      this.isSuggesting = false
      if (!response.isOk) { this.error = this.detail(response.body); return }
      const suggestion = (response.body as FormSuggestionResponse).values
      Object.assign(this.model, suggestion)
      this.form.patchValue(suggestion)
    })
  }

  save() {
    if (this.form.invalid || this.isSubmitting) { this.form.markAllAsTouched(); return }
    this.isSubmitting = true
    this.error = null
    const request = this.data.block ? this.blocks.update(this.data.block.id, this.model) : this.blocks.create(this.model)
    request.subscribe((response) => {
      this.isSubmitting = false
      if (!response.isOk) { this.error = this.detail(response.body); return }
      this.ref.close({saved: true})
    })
  }

  private detail(value: any) {
    return value?.error?.detail ?? (value?.error ? JSON.stringify(value.error) : this.translate.instant('MANUAL_EDIT.SAVE_FAILED'))
  }

  private empty(): GridBlockPayload {
    return {grid_layout: this.data?.gridLayoutId ?? '', starts_at: '12:00', ends_at: '13:00', priority: 50, min_items: 1, max_items: 1, min_duration_seconds_per_item: null, max_duration_seconds_per_item: null, allowed_categories: [], forbidden_categories: [], preferred_categories: [], allowed_natures: [], forbidden_natures: [], preferred_natures: [], allowed_container_kinds: [], forbidden_container_kinds: [], preferred_container_kinds: [], post_filler_policy: null}
  }
}
