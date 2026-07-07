import {Component, Inject} from '@angular/core';
import {NgFor} from "@angular/common";
import {MAT_DIALOG_DATA, MatDialogModule} from "@angular/material/dialog";
import {MatButtonModule} from "@angular/material/button";
import {ScheduledMediaItem} from "@project-interfaces/tv-channel";
import {DialogContainer1Component} from "@project-templates/dialog-container1/dialog-container1.component";

@Component({
  selector: 'app-schedule-media-item-detail-dialog',
  standalone: true,
  imports: [
    DialogContainer1Component,
    MatDialogModule,
    MatButtonModule,
    NgFor
  ],
  templateUrl: './schedule-media-item-detail-dialog.component.html',
  styleUrl: './schedule-media-item-detail-dialog.component.css'
})
export class ScheduleMediaItemDetailDialogComponent {
  readonly fields: Array<{label: string, value: string | number | null}>

  constructor(
    @Inject(MAT_DIALOG_DATA) public data: { item: ScheduledMediaItem }
  ) {
    const item = data.item
    this.fields = [
      {label: 'Titre item', value: item.media_item_title},
      {label: 'Description', value: item.media_item_description},
      {label: 'Role', value: item.role_label ?? 'main'},
      {label: 'Container', value: item.media_container_title},
      {label: 'Container ID', value: item.media_container_id.toString()},
      {label: 'Block source', value: item.block_name},
      {label: 'Debut', value: item.starts_at},
      {label: 'Fin', value: item.ends_at},
      {label: 'MediaItem ID', value: item.item.toString()},
    ]
  }
}
