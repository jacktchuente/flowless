import {Component, DestroyRef, inject} from '@angular/core';
import {DatePipe, NgFor, NgIf} from "@angular/common";
import {FormsModule} from "@angular/forms";
import {MatButtonModule} from "@angular/material/button";
import {MatDialog} from "@angular/material/dialog";
import {MatIconModule} from "@angular/material/icon";
import {MatProgressSpinnerModule} from "@angular/material/progress-spinner";
import {filter} from "rxjs/operators";
import {TranslateModule, TranslateService} from "@ngx-translate/core";
import {MediaContainerDetailDialogComponent} from "../media-container-dialog/media-container-dialog.component";
import {MediaContainerDetail, MediaContainerListItem, PaginatedResponse} from "@project-interfaces/media-container";
import {MediaContainerService} from "@project-services/media-container.service";
import {NotificationService} from "@project-shared/services/notification.service";
import {ConfirmationDialogComponent} from "@project-shared/confirmation-dialog/confirmation-dialog.component";
import {WebsocketService} from "@kwyxyz/ngx-request";
import {takeUntilDestroyed} from "@angular/core/rxjs-interop";

@Component({
  selector: 'app-media-container',
  standalone: true,
  imports: [
    DatePipe,
    FormsModule,
    MatButtonModule,
    MatIconModule,
    MatProgressSpinnerModule,
    TranslateModule,
    NgFor,
    NgIf
  ],
  templateUrl: './media-container.component.html',
  styleUrl: './media-container.component.css'
})
export class MediaContainerComponent {
  private readonly destroyRef = inject(DestroyRef)
  readonly pageSizeOptions = [10, 50, 100]
  readonly statusOptions = [
    {value: '', label: 'Tous'},
    {value: '0', label: 'Idle'},
    {value: '1', label: 'Analyzing'},
    {value: '2', label: 'Complete'},
    {value: '3', label: 'Skipped'},
    {value: '4', label: 'Complete with errors'},
    {value: '5', label: 'Cancelled'},
  ]
  readonly natureOptions = [
    {value: '', label: 'Toutes'},
    {value: '1', label: 'fiction'},
    {value: '2', label: 'documentary'},
    {value: '3', label: 'music'},
    {value: '4', label: 'sport'},
    {value: '5', label: 'news'},
    {value: '6', label: 'show'},
    {value: '99', label: 'other'},
  ]
  readonly containerKindOptions = [
    {value: '', label: 'Tous'},
    {value: '1', label: 'standalone_video'},
    {value: '2', label: 'series'},
    {value: '3', label: 'music_release'},
    {value: '4', label: 'music_video_release'},
    {value: '99', label: 'other'},
  ]

  containers: MediaContainerListItem[] = []
  filters = {
    title: '',
    status: '',
    category: '',
    nature: '',
    container_kind: '',
  }
  currentPage = 1
  pageSize = 10
  totalCount = 0
  isLoading = false
  isPageLoading = false
  readonly syncingIds = new Set<string>()

  constructor(
    private mediaContainerService: MediaContainerService,
    private notificationService: NotificationService,
    private dialog: MatDialog,
    private websocketService: WebsocketService,
    private translateService: TranslateService,
  ) {
    this.loadPage(1)

    this.websocketService.crudEvent
      .pipe(
        filter((event: any) => event.type?.toLowerCase?.() === 'mediacontainer'),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe(() => {
        this.loadPage(this.currentPage)
      })
  }

  get totalPages(): number {
    return Math.max(1, Math.ceil(this.totalCount / this.pageSize))
  }

  loadPage(page: number) {
    if (page < 1) {
      return
    }

    this.isLoading = true
    this.mediaContainerService.listPage(this.buildQueryParams(page)).subscribe((response) => {
      this.isLoading = false
      if (!response.isOk) {
        this.notificationService.notify("MEDIA_CONTAINER.NOTIFY_LOAD_FAILED")
        return
      }

      const payload = response.body as PaginatedResponse<MediaContainerListItem>
      this.currentPage = page
      this.totalCount = payload.count
      this.containers = payload.results
    })
  }

  applyFilters() {
    this.loadPage(1)
  }

  resetFilters() {
    this.filters = {
      title: '',
      status: '',
      category: '',
      nature: '',
      container_kind: '',
    }
    this.loadPage(1)
  }

  onPageSizeChange(value: string) {
    this.pageSize = Number(value)
    this.loadPage(1)
  }

  previousPage() {
    if (this.currentPage > 1) {
      this.loadPage(this.currentPage - 1)
    }
  }

  nextPage() {
    if (this.currentPage < this.totalPages) {
      this.loadPage(this.currentPage + 1)
    }
  }

  openDetail(container: MediaContainerListItem) {
    this.dialog.open(MediaContainerDetailDialogComponent, {
      width: '1040px',
      maxWidth: '96vw',
      data: {containerId: container.id}
    })
  }

  analyze(container: MediaContainerListItem, event?: Event) {
    event?.stopPropagation()
    const key = container.id.toString()
    if (this.syncingIds.has(key)) {
      return
    }

    this.syncingIds.add(key)
    this.isPageLoading = true
    this.mediaContainerService.analyze(container.id).subscribe((response) => {
      this.syncingIds.delete(key)
      this.isPageLoading = false
      if (!response.isOk) {
        this.notificationService.notify("MEDIA_CONTAINER.NOTIFY_ANALYZE_FAILED")
        return
      }
      container.analyze_status = 1
      this.notificationService.notify("Analyse du media lancee en arriere-plan.")
    })
  }

  analyzeAll() {
    this.dialog.open(ConfirmationDialogComponent, {
      width: '520px',
      maxWidth: '92vw',
      data: {
        confirmationMessage: this.translateService.instant('MEDIA_CONTAINER.CONFIRM_ANALYZE_ALL')
      }
    }).afterClosed().subscribe((confirmed) => {
      if (!confirmed) {
        return
      }
      this.isPageLoading = true
      this.mediaContainerService.analyzeAll().subscribe((response) => {
        this.isPageLoading = false
        if (!response.isOk) {
          this.notificationService.notify("MEDIA_CONTAINER.NOTIFY_ANALYZE_ALL_FAILED")
          return
        }
        this.containers = this.containers.map((container) => ({
          ...container,
          analyze_status: 1,
        }))
        this.notificationService.notify("Analyse globale des medias lancee en arriere-plan.")
      })
    })
  }

  getStatusLabel(container: MediaContainerListItem): string {
    switch (container.analyze_status) {
      case 1:
        return this.translateService.instant('COMMON.STATUS.ANALYZING')
      case 2:
        return this.translateService.instant('COMMON.STATUS.COMPLETE')
      case 3:
        return this.translateService.instant('COMMON.STATUS.SKIPPED')
      case 4:
        return this.translateService.instant('COMMON.STATUS.COMPLETE_WITH_ERRORS')
      case 5:
        return this.translateService.instant('COMMON.STATUS.CANCELLED')
      default:
        return this.translateService.instant('COMMON.STATUS.IDLE')
    }
  }

  getStatusClass(container: MediaContainerListItem): string {
    switch (container.analyze_status) {
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

  getNatureLabel(container: MediaContainerListItem): string {
    return this.natureOptions.find((option) => option.value === String(container.nature ?? ''))?.label || '—'
  }

  getContainerKindLabel(container: MediaContainerListItem): string {
    return this.containerKindOptions.find((option) => option.value === String(container.container_kind ?? ''))?.label || '—'
  }

  private buildQueryParams(page: number): Record<string, string | number> {
    const params: Record<string, string | number> = {
      page,
      page_size: this.pageSize,
    }
    if (this.filters.title.trim()) {
      params['title'] = this.filters.title.trim()
    }
    if (this.filters.status) {
      params['status'] = this.filters.status
    }
    if (this.filters.category.trim()) {
      params['category'] = this.filters.category.trim()
    }
    if (this.filters.nature) {
      params['nature'] = this.filters.nature
    }
    if (this.filters.container_kind) {
      params['container_kind'] = this.filters.container_kind
    }
    return params
  }
}
