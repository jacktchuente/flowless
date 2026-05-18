import {Component, Inject} from '@angular/core';
import {DatePipe, NgFor, NgIf} from "@angular/common";
import {FormsModule} from "@angular/forms";
import {MAT_DIALOG_DATA, MatDialogModule, MatDialogRef} from "@angular/material/dialog";
import {MatButtonModule} from "@angular/material/button";
import {MatProgressSpinnerModule} from "@angular/material/progress-spinner";
import {MediaCollection} from "@project-interfaces/media-collection";
import {MediaCollectionService} from "@project-services/media-collection.service";
import {NotificationService} from "@project-shared/services/notification.service";

interface SelectOption {
  value: number
  label: string
}

@Component({
  selector: 'app-media-collection-detail-dialog',
  standalone: true,
  imports: [
    DatePipe,
    FormsModule,
    MatButtonModule,
    MatDialogModule,
    MatProgressSpinnerModule,
    NgFor,
    NgIf,
  ],
  templateUrl: './media-collection-detail-dialog.component.html',
  styleUrl: './media-collection-detail-dialog.component.css'
})
export class MediaCollectionDetailDialogComponent {
  draft: {
    programming_role: number | null
    nature: number | null
    container_kind: number | null
  }
  isSubmitting = false

  readonly programmingRoleOptions: SelectOption[] = [
    {value: 1, label: 'main'},
    {value: 2, label: 'trailer'},
    {value: 3, label: 'promo'},
    {value: 4, label: 'ad'},
    {value: 5, label: 'bumper'},
    {value: 6, label: 'ident'},
    {value: 7, label: 'filler'},
    {value: 8, label: 'psa'},
    {value: 99, label: 'other'},
  ]

  readonly natureOptions: SelectOption[] = [
    {value: 1, label: 'fiction'},
    {value: 2, label: 'documentary'},
    {value: 3, label: 'music'},
    {value: 4, label: 'sport'},
    {value: 5, label: 'news'},
    {value: 6, label: 'show'},
    {value: 99, label: 'other'},
  ]

  readonly containerKindOptions: SelectOption[] = [
    {value: 1, label: 'standalone_video'},
    {value: 2, label: 'series'},
    {value: 3, label: 'music_release'},
    {value: 4, label: 'music_video_release'},
    {value: 99, label: 'other'},
  ]

  constructor(
    private mediaCollectionService: MediaCollectionService,
    private notificationService: NotificationService,
    private dialogRef: MatDialogRef<MediaCollectionDetailDialogComponent>,
    @Inject(MAT_DIALOG_DATA) public data: { collection: MediaCollection }
  ) {
    this.draft = {
      programming_role: data.collection.programming_role ?? null,
      nature: data.collection.nature ?? null,
      container_kind: data.collection.container_kind ?? null,
    }
  }

  save() {
    if (this.isSubmitting) {
      return
    }
    this.isSubmitting = true
    this.mediaCollectionService.patchObject(this.data.collection.id.toString(), this.draft).subscribe((response) => {
      this.isSubmitting = false
      if (!response.isOk) {
        this.notificationService.notify("Mise a jour de la collection impossible.")
        return
      }
      this.dialogRef.close(true)
    })
  }
}
