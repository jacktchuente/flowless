import {Component, Inject} from '@angular/core';
import {FormGroup, ReactiveFormsModule} from '@angular/forms';
import {NgIf} from '@angular/common';
import {MAT_DIALOG_DATA, MatDialogModule, MatDialogRef} from '@angular/material/dialog';
import {MatButtonModule} from '@angular/material/button';
import {MatProgressSpinnerModule} from '@angular/material/progress-spinner';
import {FormlyFieldConfig, FormlyModule} from '@ngx-formly/core';
import {TranslateModule, TranslateService} from '@ngx-translate/core';
import {EditorialLineData, EditorialLinePayload, FormOptions, FormSuggestionResponse} from '@project-interfaces/tv-channel';
import {TvChannelService} from '@project-services/tv-channel.service';
import {DialogContainer1Component} from '@project-templates/dialog-container1/dialog-container1.component';
import {SuggestionPanelComponent} from '@project-templates/suggestion-panel/suggestion-panel.component';

@Component({selector: 'app-editorial-line-edit-dialog', standalone: true, imports: [ReactiveFormsModule, NgIf, MatDialogModule, MatButtonModule, MatProgressSpinnerModule, FormlyModule, TranslateModule, DialogContainer1Component, SuggestionPanelComponent], templateUrl: './editorial-line-edit-dialog.component.html', styleUrl: './editorial-line-edit-dialog.component.css'})
export class EditorialLineEditDialogComponent {
  form = new FormGroup({}); model: EditorialLinePayload; fields: FormlyFieldConfig[]; isSubmitting = false; isSuggesting = false; error: string | null = null
  constructor(private service: TvChannelService, private ref: MatDialogRef<EditorialLineEditDialogComponent>, private translate: TranslateService, @Inject(MAT_DIALOG_DATA) public data: {channelId: string | number, editorialLine: EditorialLineData | null, formOptions: FormOptions}) {
    this.model = {...this.emptyModel(), ...(data.editorialLine ?? {})}
    const multi = (key: string, label: string, options: any[]): FormlyFieldConfig => ({key, type: 'select', props: {label, multiple: true, options}})
    const cats = data.formOptions.categories.map(value => ({label: value, value}))
    this.fields = [
      multi('allowed_categories', this.translate.instant('MANUAL_EDIT.ALLOWED_CATEGORIES'), cats), multi('forbidden_categories', this.translate.instant('MANUAL_EDIT.FORBIDDEN_CATEGORIES'), cats), multi('preferred_categories', this.translate.instant('MANUAL_EDIT.PREFERRED_CATEGORIES'), cats),
      multi('allowed_natures', this.translate.instant('MANUAL_EDIT.ALLOWED_NATURES'), data.formOptions.natures), multi('forbidden_natures', this.translate.instant('MANUAL_EDIT.FORBIDDEN_NATURES'), data.formOptions.natures), multi('preferred_natures', this.translate.instant('MANUAL_EDIT.PREFERRED_NATURES'), data.formOptions.natures),
      multi('allowed_container_kinds', this.translate.instant('MANUAL_EDIT.ALLOWED_KINDS'), data.formOptions.container_kinds), multi('forbidden_container_kinds', this.translate.instant('MANUAL_EDIT.FORBIDDEN_KINDS'), data.formOptions.container_kinds), multi('preferred_container_kinds', this.translate.instant('MANUAL_EDIT.PREFERRED_KINDS'), data.formOptions.container_kinds),
      {fieldGroupClassName: 'time-row', fieldGroup: [{key: 'start_at', type: 'input', props: {label: this.translate.instant('MANUAL_EDIT.START'), type: 'time', required: true}}, {key: 'end_at', type: 'input', props: {label: this.translate.instant('MANUAL_EDIT.END'), type: 'time', required: true}}]},
      {key: 'allow_filler', type: 'checkbox', props: {label: this.translate.instant('MANUAL_EDIT.ALLOW_FILLER')}},
    ]
  }
  suggest(context: string) { this.isSuggesting = true; this.error = null; this.service.suggestForm(this.data.channelId, {form_kind: 'editorial_line', user_context: context, current_values: {...this.model}}).subscribe(r => { this.isSuggesting = false; if (!r.isOk) { this.error = this.detail(r.body); return } const values = (r.body as FormSuggestionResponse).values; Object.assign(this.model, values); this.form.patchValue(values); }) }
  save() { if (this.form.invalid || this.isSubmitting) { this.form.markAllAsTouched(); return } this.isSubmitting = true; this.error = null; this.service.updateEditorialLine(this.data.channelId, this.model).subscribe(r => { this.isSubmitting = false; if (!r.isOk) { this.error = this.detail(r.body); return } this.ref.close({saved: true}) }) }
  private detail(value: any) { return value?.error?.detail ?? (value?.error ? JSON.stringify(value.error) : this.translate.instant('MANUAL_EDIT.SAVE_FAILED')) }
  private emptyModel(): EditorialLinePayload { return {allowed_categories: [], forbidden_categories: [], preferred_categories: [], allowed_natures: [], forbidden_natures: [], preferred_natures: [], allowed_container_kinds: [], forbidden_container_kinds: [], preferred_container_kinds: [], start_at: '06:00', end_at: '22:00', allow_filler: true} }
}
