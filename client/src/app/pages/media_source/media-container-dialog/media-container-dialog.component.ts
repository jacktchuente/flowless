import {Component, Inject} from '@angular/core';
import {DatePipe, JsonPipe, NgFor, NgIf} from "@angular/common";
import {MAT_DIALOG_DATA, MatDialogModule} from "@angular/material/dialog";
import {MatButtonModule} from "@angular/material/button";
import {MatProgressSpinnerModule} from "@angular/material/progress-spinner";
import {MediaContainerDetail} from "@project-interfaces/media-container";
import {MediaContainerService} from "@project-services/media-container.service";

@Component({
  selector: 'app-media-container-detail-dialog',
  standalone: true,
  imports: [
    DatePipe,
    JsonPipe,
    MatButtonModule,
    MatDialogModule,
    MatProgressSpinnerModule,
    NgFor,
    NgIf
  ],
  templateUrl: './media-container-dialog.component.html',
  styleUrl: './media-container-dialog.component.css'
})
export class MediaContainerDetailDialogComponent {
  container: MediaContainerDetail | null = null
  isLoading = true

  constructor(
    private mediaContainerService: MediaContainerService,
    @Inject(MAT_DIALOG_DATA) public data: { containerId: string | number }
  ) {
    this.mediaContainerService.getDetail(data.containerId).subscribe((response) => {
      this.isLoading = false
      if (!response.isOk) {
        return
      }
      this.container = response.body as MediaContainerDetail
    })
  }

  formatList(values: string[] | null | undefined): string {
    if (!values?.length) {
      return '—'
    }
    return values.join(', ')
  }
}
