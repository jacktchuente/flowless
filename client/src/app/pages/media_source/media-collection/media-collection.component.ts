import {Component, DestroyRef, inject} from '@angular/core';
import {DatePipe, NgFor, NgIf} from "@angular/common";
import {takeUntilDestroyed} from "@angular/core/rxjs-interop";
import {MatButtonModule} from "@angular/material/button";
import {MatDialog} from "@angular/material/dialog";
import {MatIconModule} from "@angular/material/icon";
import {MatProgressSpinnerModule} from "@angular/material/progress-spinner";
import {MatSlideToggleModule} from "@angular/material/slide-toggle";
import {TranslateModule, TranslateService} from "@ngx-translate/core";
import {MediaCollection} from "@project-interfaces/media-collection";
import {MediaCollectionService} from "@project-services/media-collection.service";
import {ConfirmationDialogComponent} from "@project-shared/confirmation-dialog/confirmation-dialog.component";
import {NotificationService} from "@project-shared/services/notification.service";
import {MediaCollectionDetailDialogComponent} from "../media-collection-detail-dialog/media-collection-detail-dialog.component";

@Component({
  selector: 'app-media-collection',
  standalone: true,
  imports: [
    DatePipe,
    MatButtonModule,
    MatIconModule,
    MatProgressSpinnerModule,
    MatSlideToggleModule,
    TranslateModule,
    NgFor,
    NgIf
  ],
  templateUrl: './media-collection.component.html',
  styleUrl: './media-collection.component.css'
})
export class MediaCollectionComponent {
  private readonly destroyRef = inject(DestroyRef)

  collections: MediaCollection[] = []
  readonly syncingIds = new Set<string>()
  isPageLoading = false

  constructor(
    private mediaCollectionService: MediaCollectionService,
    private notificationService: NotificationService,
    private dialog: MatDialog,
    private translateService: TranslateService,
  ) {
    this.mediaCollectionService.listObject(null, true)

    this.mediaCollectionService.getObjectBehaviorSubject()
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe((collections) => {
        this.collections = collections
      })
  }

  openDetail(collection: MediaCollection) {
    this.dialog.open(MediaCollectionDetailDialogComponent, {
      width: '820px',
      maxWidth: '96vw',
      data: {collection}
    })
  }

  toggleActive(collection: MediaCollection, isActive: boolean) {
    this.mediaCollectionService.patchObject(collection.id.toString(), {is_active: isActive}).subscribe((response) => {
      if (!response.isOk) {
        this.notificationService.notify("MEDIA_COLLECTION.NOTIFY_TOGGLE_FAILED")
      }
    })
  }

  analyze(collection: MediaCollection, event?: Event) {
    event?.stopPropagation()
    const key = collection.id.toString()
    if (this.syncingIds.has(key) || !collection.is_active) {
      return
    }

    const alreadyAnalyzed = !!collection.analyzed_at
    this.dialog.open(ConfirmationDialogComponent, {
      width: '520px',
      maxWidth: '92vw',
      data: {
        confirmationMessage: this.translateService.instant('MEDIA_COLLECTION.CONFIRM_ANALYZE', {name: collection.name}),
        extraActionLabel: alreadyAnalyzed ? 'MEDIA_COLLECTION.FORCE_REANALYZE' : null,
      }
    }).afterClosed().subscribe((result) => {
      if (!result) {
        return
      }
      const force = result === 'extra'
      this.syncingIds.add(key)
      this.isPageLoading = true
      this.mediaCollectionService.analyze(collection.id, force).subscribe((response) => {
        this.syncingIds.delete(key)
        this.isPageLoading = false
        if (!response.isOk) {
          this.notificationService.notify("MEDIA_COLLECTION.NOTIFY_ANALYZE_FAILED")
          return
        }
        collection.analyze_status = 1
        this.notificationService.notify("MEDIA_COLLECTION.NOTIFY_ANALYZE_STARTED")
      })
    })
  }

  getAnalyzeIcon(collection: MediaCollection): string {
    switch (collection.analyze_status) {
      case 1:
        return 'progress_activity'
      case 2:
        return 'check_circle'
      case 4:
        return 'error'
      case 5:
        return 'cancel'
      default:
        return 'radio_button_unchecked'
    }
  }

  getAnalyzeLabel(collection: MediaCollection): string {
    switch (collection.analyze_status) {
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

  getAnalyzeClass(collection: MediaCollection): string {
    switch (collection.analyze_status) {
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

  getProgrammingRoleLabel(collection: MediaCollection): string {
    return this.findChoiceLabel(collection.programming_role, PROGRAMMING_ROLE_OPTIONS)
  }

  getNatureLabel(collection: MediaCollection): string {
    return this.findChoiceLabel(collection.nature, NATURE_OPTIONS)
  }

  getContainerKindLabel(collection: MediaCollection): string {
    return this.findChoiceLabel(collection.container_kind, CONTAINER_KIND_OPTIONS)
  }

  private findChoiceLabel(value: number | null, choices: ReadonlyArray<{value: number, label: string}>): string {
    if (value === null || value === undefined) {
      return '—'
    }
    return choices.find((choice) => choice.value === value)?.label ?? `${value}`
  }
}

const PROGRAMMING_ROLE_OPTIONS = [
  {value: 1, label: 'main'},
  {value: 2, label: 'trailer'},
  {value: 3, label: 'promo'},
  {value: 4, label: 'ad'},
  {value: 5, label: 'bumper'},
  {value: 6, label: 'ident'},
  {value: 7, label: 'filler'},
  {value: 8, label: 'psa'},
  {value: 99, label: 'other'},
] as const

const NATURE_OPTIONS = [
  {value: 1, label: 'fiction'},
  {value: 2, label: 'documentary'},
  {value: 3, label: 'music'},
  {value: 4, label: 'sport'},
  {value: 5, label: 'news'},
  {value: 6, label: 'show'},
  {value: 99, label: 'other'},
] as const

const CONTAINER_KIND_OPTIONS = [
  {value: 1, label: 'standalone_video'},
  {value: 2, label: 'series'},
  {value: 3, label: 'music_release'},
  {value: 4, label: 'music_video_release'},
  {value: 99, label: 'other'},
] as const
