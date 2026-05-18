import {Component, Inject} from '@angular/core';
import {NgFor, NgIf} from "@angular/common";
import {MAT_DIALOG_DATA, MatDialogModule} from "@angular/material/dialog";
import {MatButtonModule} from "@angular/material/button";
import {MatProgressSpinnerModule} from "@angular/material/progress-spinner";
import {MatTabsModule} from "@angular/material/tabs";
import {EditorialLineData, GridBlock, GridData} from "@project-interfaces/tv-channel";
import {GridBlockAvailableMediaCount, GridBlockService} from "@project-services/grid-block.service";
import {NotificationService} from "@project-shared/services/notification.service";
import {DialogContainer1Component} from "@project-templates/dialog-container1/dialog-container1.component";

@Component({
  selector: 'app-grid-block-detail-dialog',
  standalone: true,
  imports: [
    DialogContainer1Component,
    MatDialogModule,
    MatButtonModule,
    MatProgressSpinnerModule,
    MatTabsModule,
    NgFor,
    NgIf
  ],
  templateUrl: './grid-block-detail-dialog.component.html',
  styleUrl: './grid-block-detail-dialog.component.css'
})
export class GridBlockDetailDialogComponent {
  blockFields: Array<{label: string, value: string | number | boolean | null}>
  readonly editorialFields: Array<{label: string, value: string | number | boolean | null}>
  isLoadingAvailableMediaCount = true

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
    private gridBlockService: GridBlockService,
    private notificationService: NotificationService,
    @Inject(MAT_DIALOG_DATA) public data: { block: GridBlock, grid: GridData, editorialLine: EditorialLineData }
  ) {
    const block = data.block
    const editorial = data.editorialLine
    this.blockFields = [
      {label: 'Grille', value: `#${data.grid.id}`},
      {label: 'Debut', value: block.starts_at},
      {label: 'Fin', value: block.ends_at},
      {label: 'Priorite', value: block.priority},
      {label: 'Min items', value: block.min_items},
      {label: 'Max items', value: block.max_items},
      {label: 'Min duree item', value: block.min_duration_seconds_per_item},
      {label: 'Max duree item', value: block.max_duration_seconds_per_item},
      {label: 'Media disponibles', value: 'Chargement...'},
      {label: 'Post filler policy', value: block.post_filler_policy_name || block.post_filler_policy?.toString() || null},
      {label: 'Allowed categories', value: this.stringifyValue(block.allowed_categories)},
      {label: 'Forbidden categories', value: this.stringifyValue(block.forbidden_categories)},
      {label: 'Preferred categories', value: this.stringifyValue(block.preferred_categories)},
      {label: 'Allowed natures', value: this.stringifyChoiceList(block.allowed_natures, this.natureLabels)},
      {label: 'Forbidden natures', value: this.stringifyChoiceList(block.forbidden_natures, this.natureLabels)},
      {label: 'Preferred natures', value: this.stringifyChoiceList(block.preferred_natures, this.natureLabels)},
      {label: 'Allowed container kinds', value: this.stringifyChoiceList(block.allowed_container_kinds, this.containerKindLabels)},
      {label: 'Forbidden container kinds', value: this.stringifyChoiceList(block.forbidden_container_kinds, this.containerKindLabels)},
      {label: 'Preferred container kinds', value: this.stringifyChoiceList(block.preferred_container_kinds, this.containerKindLabels)},
    ]

    this.editorialFields = [
      {label: 'Allowed categories', value: this.stringifyValue(editorial.allowed_categories)},
      {label: 'Forbidden categories', value: this.stringifyValue(editorial.forbidden_categories)},
      {label: 'Preferred categories', value: this.stringifyValue(editorial.preferred_categories)},
      {label: 'Allowed natures', value: this.stringifyChoiceList(editorial.allowed_natures, this.natureLabels)},
      {label: 'Forbidden natures', value: this.stringifyChoiceList(editorial.forbidden_natures, this.natureLabels)},
      {label: 'Preferred natures', value: this.stringifyChoiceList(editorial.preferred_natures, this.natureLabels)},
      {label: 'Allowed container kinds', value: this.stringifyChoiceList(editorial.allowed_container_kinds, this.containerKindLabels)},
      {label: 'Forbidden container kinds', value: this.stringifyChoiceList(editorial.forbidden_container_kinds, this.containerKindLabels)},
      {label: 'Preferred container kinds', value: this.stringifyChoiceList(editorial.preferred_container_kinds, this.containerKindLabels)},
      {label: 'Debut diffusion', value: editorial.start_at},
      {label: 'Fin diffusion', value: editorial.end_at},
      {label: 'Allow filler', value: editorial.allow_filler ? 'Oui' : 'Non'},
    ]

    this.gridBlockService.getAvailableMediaCount(block.id).subscribe((response) => {
      this.isLoadingAvailableMediaCount = false
      if (!response.isOk) {
        this.notificationService.notify("Chargement du nombre de medias disponibles impossible.")
        this.blockFields = this.blockFields.map((field) =>
          field.label === 'Media disponibles' ? {...field, value: '—'} : field
        )
        return
      }
      const payload = response.body as GridBlockAvailableMediaCount
      this.blockFields = this.blockFields.map((field) =>
        field.label === 'Media disponibles' ? {...field, value: payload.count} : field
      )
    })
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

  private stringifyChoiceList(
    value: Array<string | number> | null | undefined,
    labels: Record<string, string>
  ): string | null {
    if (!value?.length) {
      return null
    }
    return value
      .map((entry) => labels[String(entry)] ?? String(entry))
      .join(', ')
  }
}
