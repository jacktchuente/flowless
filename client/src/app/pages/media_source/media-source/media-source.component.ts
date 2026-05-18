import {Component, DestroyRef, inject} from '@angular/core';
import {DatePipe, NgFor, NgIf} from "@angular/common";
import {MatDialog} from "@angular/material/dialog";
import {MatButtonModule} from "@angular/material/button";
import {MatIconModule} from "@angular/material/icon";
import {MatProgressSpinnerModule} from "@angular/material/progress-spinner";
import {takeUntilDestroyed} from "@angular/core/rxjs-interop";
import {TranslateModule, TranslateService} from "@ngx-translate/core";
import {MediaSource} from "@project-interfaces/media-source";
import {MediaSourceService} from "@project-services/media-source.service";
import {MediaSourceDialogComponent} from "../media-source-dialog/media-source-dialog.component";
import {NotificationService} from "@project-shared/services/notification.service";

@Component({
  selector: 'app-media-source',
  standalone: true,
  imports: [
    DatePipe,
    MatButtonModule,
    MatIconModule,
    MatProgressSpinnerModule,
    TranslateModule,
    NgFor,
    NgIf
  ],
  templateUrl: './media-source.component.html',
  styleUrl: './media-source.component.css'
})
export class MediaSourceComponent {
  private readonly destroyRef = inject(DestroyRef)

  sources: MediaSource[] = []
  readonly syncingIds = new Set<string>()
  isPageLoading = false

  constructor(
    private mediaSourceService: MediaSourceService,
    private notificationService: NotificationService,
    private dialog: MatDialog,
    private translateService: TranslateService,
  ) {
    this.mediaSourceService.listObject(null, true)

    this.mediaSourceService.getObjectBehaviorSubject()
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe((sources) => {
        this.sources = sources
      })
  }

  openCreateDialog() {
    this.dialog.open(MediaSourceDialogComponent, {
      width: '720px',
      maxWidth: '96vw',
      data: {}
    })
  }

  openEditDialog(source: MediaSource, event?: Event) {
    event?.stopPropagation()
    this.dialog.open(MediaSourceDialogComponent, {
      width: '720px',
      maxWidth: '96vw',
      data: {source}
    })
  }

  deleteSource(source: MediaSource, event?: Event) {
    event?.stopPropagation()
    this.mediaSourceService.deleteObject(source.id.toString()).subscribe((response) => {
      if (!response.isOk) {
        this.notificationService.notify("MEDIA_SOURCE.NOTIFY_DELETE_FAILED")
      }
    })
  }

  syncCollections(source: MediaSource, event?: Event) {
    event?.stopPropagation()
    const key = source.id.toString()
    if (this.syncingIds.has(key)) {
      return
    }

    this.syncingIds.add(key)
    this.isPageLoading = true
    this.mediaSourceService.syncCollections(source.id).subscribe((response) => {
      this.syncingIds.delete(key)
      this.isPageLoading = false
      if (!response.isOk) {
        this.notificationService.notify("MEDIA_SOURCE.NOTIFY_SYNC_FAILED")
        return
      }

      source.analyze_status = 1
      this.notificationService.notify("MEDIA_SOURCE.NOTIFY_SYNC_STARTED")
    })
  }

  getSourceStatusLabel(source: MediaSource): string {
    switch (source.analyze_status) {
      case 1:
        return this.translateService.instant('COMMON.STATUS.ANALYZING')
      case 2:
        return this.translateService.instant('COMMON.STATUS.COMPLETE')
      case 4:
        return this.translateService.instant('COMMON.STATUS.COMPLETE_WITH_ERRORS')
      case 5:
        return this.translateService.instant('COMMON.STATUS.CANCELLED')
      case 3:
        return this.translateService.instant('COMMON.STATUS.SKIPPED')
      default:
        return this.translateService.instant('COMMON.STATUS.IDLE')
    }
  }

  getSourceStatusClass(source: MediaSource): string {
    switch (source.analyze_status) {
      case 1:
        return 'is-analyzing'
      case 2:
        return 'is-complete'
      case 4:
        return 'is-warning'
      default:
        return 'is-idle'
    }
  }
}
