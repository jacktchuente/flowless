import {Component, Inject} from '@angular/core';
import {NgFor, NgIf} from "@angular/common";
import {MAT_DIALOG_DATA, MatDialogModule} from "@angular/material/dialog";
import {MatButtonModule} from "@angular/material/button";
import {MatProgressSpinnerModule} from "@angular/material/progress-spinner";
import {EditorialLineData} from "@project-interfaces/tv-channel";
import {DialogContainer1Component} from "@project-templates/dialog-container1/dialog-container1.component";

@Component({
  selector: 'app-editorial-line-detail-dialog',
  standalone: true,
  imports: [
    DialogContainer1Component,
    MatDialogModule,
    MatButtonModule,
    MatProgressSpinnerModule,
    NgFor,
    NgIf
  ],
  templateUrl: './editorial-line-detail-dialog.component.html',
  styleUrl: './editorial-line-detail-dialog.component.css'
})
export class EditorialLineDetailDialogComponent {
  editorialLine: EditorialLineData | null = null
  isLoading = false
  fields: Array<{label: string, value: string | number | null}> = []
  private readonly natureLabels: Record<string, string> = {
    '1': 'fiction',
    '2': 'documentary',
    '3': 'music',
    '4': 'sport',
    '5': 'news',
    '6': 'show',
    '99': 'other',
  }
  private readonly containerKindLabels: Record<string, string> = {
    '1': 'standalone_video',
    '2': 'series',
    '3': 'music_release',
    '4': 'music_video_release',
    '99': 'other',
  }

  constructor(
    @Inject(MAT_DIALOG_DATA) public data: { channelName: string, editorialLine: EditorialLineData }
  ) {
    this.editorialLine = data.editorialLine
    this.fields = [
      {label: 'Categories autorisees', value: this.stringifyValue(this.editorialLine.allowed_categories)},
      {label: 'Categories interdites', value: this.stringifyValue(this.editorialLine.forbidden_categories)},
      {label: 'Categories preferees', value: this.stringifyValue(this.editorialLine.preferred_categories)},
      {label: 'Natures autorisees', value: this.stringifyChoiceList(this.editorialLine.allowed_natures, this.natureLabels)},
      {label: 'Natures interdites', value: this.stringifyChoiceList(this.editorialLine.forbidden_natures, this.natureLabels)},
      {label: 'Natures preferees', value: this.stringifyChoiceList(this.editorialLine.preferred_natures, this.natureLabels)},
      {label: 'Types autorises', value: this.stringifyChoiceList(this.editorialLine.allowed_container_kinds, this.containerKindLabels)},
      {label: 'Types interdits', value: this.stringifyChoiceList(this.editorialLine.forbidden_container_kinds, this.containerKindLabels)},
      {label: 'Types preferes', value: this.stringifyChoiceList(this.editorialLine.preferred_container_kinds, this.containerKindLabels)},
      {label: 'Debut diffusion', value: this.editorialLine.start_at},
      {label: 'Fin diffusion', value: this.editorialLine.end_at},
      {label: 'Allow filler', value: this.editorialLine.allow_filler ? 'Oui' : 'Non'},
    ]
  }

  private stringifyValue(value: unknown): string | null {
    if (value === null || value === undefined) {
      return null
    }
    if (Array.isArray(value) && !value.length) {
      return null
    }
    if (Array.isArray(value)) {
      return value.join(', ')
    }
    if (typeof value === 'object') {
      return JSON.stringify(value, null, 2)
    }
    return String(value)
  }

  private stringifyChoiceList(value: unknown, labels: Record<string, string>): string | null {
    if (!Array.isArray(value) || !value.length) {
      return null
    }
    return value.map((item) => labels[String(item)] ?? String(item)).join(', ')
  }
}
