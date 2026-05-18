import {AfterViewInit, Component, DestroyRef, inject} from '@angular/core';
import {DatePipe, NgFor, NgIf} from "@angular/common";
import {FormsModule} from "@angular/forms";
import {MatDialog} from "@angular/material/dialog";
import {MatButtonModule} from "@angular/material/button";
import {MatButtonToggleModule} from "@angular/material/button-toggle";
import {MatIconModule} from "@angular/material/icon";
import {MatMenuModule} from "@angular/material/menu";
import {MatProgressSpinnerModule} from "@angular/material/progress-spinner";
import {takeUntilDestroyed} from "@angular/core/rxjs-interop";
import {Router} from "@angular/router";
import {CalendarEvent, CalendarModule} from "angular-calendar";
import {TranslateModule, TranslateService} from "@ngx-translate/core";
import {Catalog} from "@project-interfaces/catalog";
import {GridBlock, ScheduledMediaItem, TvChannel} from "@project-interfaces/tv-channel";
import {CatalogService} from "@project-services/catalog.service";
import {TvChannelService} from "@project-services/tv-channel.service";
import {NotificationService} from "@project-shared/services/notification.service";
import {CatalogDialogComponent} from "../catalog-dialog/catalog-dialog.component";
import {BlueprintGenerationDialogComponent} from "../blueprint-generation-dialog/blueprint-generation-dialog.component";
import {GridBlockDetailDialogComponent} from "../grid-block-detail-dialog/grid-block-detail-dialog.component";
import {PlayoutGenerationDialogComponent} from "../playout-generation-dialog/playout-generation-dialog.component";
import {ResetRulesDialogComponent} from "../reset-rules-dialog/reset-rules-dialog.component";
import {ScheduleMediaItemDetailDialogComponent} from "../schedule-media-item-detail-dialog/schedule-media-item-detail-dialog.component";
import {TvChannelDialogComponent} from "../tv-channel-dialog/tv-channel-dialog.component";
import {ConfirmationDialogComponent} from "@project-shared/confirmation-dialog/confirmation-dialog.component";

type ChannelCalendarEventMeta =
  | {kind: 'schedule', item: ScheduledMediaItem}
  | {kind: 'block', channel: TvChannel, block: GridBlock}
type ChannelCalendarEvent = CalendarEvent<ChannelCalendarEventMeta>

@Component({
  selector: 'app-channel-management',
  standalone: true,
  imports: [
    FormsModule,
    DatePipe,
    MatButtonModule,
    MatButtonToggleModule,
    MatIconModule,
    MatMenuModule,
    MatProgressSpinnerModule,
    CalendarModule,
    TranslateModule,
    NgFor,
    NgIf
  ],
  templateUrl: './channel-management.component.html',
  styleUrl: './channel-management.component.css'
})
export class ChannelManagementComponent implements AfterViewInit {
  private readonly destroyRef = inject(DestroyRef)
  private calendarRefreshHandle: number | null = null
  private deferredCalendarRenderHandle: number | null = null

  catalogs: Catalog[] = []
  channels: TvChannel[] = []
  calendarEventsByChannelId: Record<string, ChannelCalendarEvent[]> = {}
  selectedCatalogId: string | null = null
  calendarDate = new Date()
  calendarViewMode: 'grid' | 'schedule' = 'grid'
  isPageLoading = false
  readonly emptyCalendarEvents: ChannelCalendarEvent[] = []
  showCalendarContent = false

  constructor(
    private catalogService: CatalogService,
    private tvChannelService: TvChannelService,
    private notificationService: NotificationService,
    private dialog: MatDialog,
    private router: Router,
    private translateService: TranslateService,
  ) {
    this.catalogService.getObjectBehaviorSubject()
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe((catalogs: Catalog[]) => {
        this.catalogs = catalogs
        if (!this.selectedCatalogId && catalogs.length) {
          this.selectedCatalogId = catalogs[0].id.toString()
          this.calendarDate = this.getTodayDate()
          this.loadChannels()
        }
      })

    this.tvChannelService.getObjectBehaviorSubject()
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe((channels: TvChannel[]) => {
        this.channels = channels
        this.deferCalendarRendering()
      })
  }

  ngAfterViewInit() {
    this.deferCalendarRendering()
  }

  get selectedCatalog(): Catalog | undefined {
    return this.catalogs.find((catalog) => catalog.id.toString() === this.selectedCatalogId)
  }

  onCatalogChange() {
    this.calendarDate = this.getTodayDate()
    this.loadChannels()
  }

  loadChannels() {
    if (!this.selectedCatalogId) {
      this.channels = []
      this.calendarEventsByChannelId = {}
      this.showCalendarContent = false
      this.tvChannelService.emptyData()
      this.tvChannelService.syncData()
      return
    }
    this.showCalendarContent = false
    this.tvChannelService.listObject({catalog: this.selectedCatalogId}, true)
  }

  openCreateCatalogDialog() {
    this.dialog.open(CatalogDialogComponent, {
      width: '720px',
      maxWidth: '96vw',
      data: {}
    })
  }

  openEditCatalogDialog() {
    if (!this.selectedCatalog) {
      return
    }
    this.dialog.open(CatalogDialogComponent, {
      width: '720px',
      maxWidth: '96vw',
      data: {catalog: this.selectedCatalog}
    })
  }

  openCreateChannelDialog() {
    this.dialog.open(TvChannelDialogComponent, {
      width: '720px',
      maxWidth: '96vw',
      data: {
        selectedCatalogId: this.selectedCatalogId,
        catalogs: this.catalogs,
      }
    }).afterClosed().subscribe((result) => {
      if (result) {
        this.loadChannels()
      }
    })
  }

  openEditChannelDialog(channel: TvChannel) {
    this.dialog.open(TvChannelDialogComponent, {
      width: '720px',
      maxWidth: '96vw',
      data: {
        channel,
        selectedCatalogId: this.selectedCatalogId,
        catalogs: this.catalogs,
      }
    }).afterClosed().subscribe((result) => {
      if (result) {
        this.loadChannels()
      }
    })
  }

  openChannelDetail(channel: TvChannel) {
    this.router.navigate(['/app/channels', channel.id])
  }

  deleteChannel(channel: TvChannel) {
    this.tvChannelService.deleteObject(channel.id.toString()).subscribe((response) => {
      if (!response.isOk) {
        this.notificationService.notify("Suppression impossible.")
        return
      }
      this.loadChannels()
    })
  }

  generateCatalogChannels() {
    if (!this.selectedCatalog) {
      return
    }
    this.dialog.open(ConfirmationDialogComponent, {
      width: '520px',
      maxWidth: '92vw',
      data: {
        confirmationMessage: this.translateService.instant('CHANNELS.CONFIRM_GENERATE_CATALOG', {
          name: this.selectedCatalog.name,
        })
      }
    }).afterClosed().subscribe((confirmed) => {
      if (!confirmed) {
        return
      }
      this.isPageLoading = true
      this.catalogService.generateChannels(this.selectedCatalog!.id).subscribe((response) => {
        this.isPageLoading = false
        if (!response.isOk) {
          this.notificationService.notify("CHANNELS.NOTIFY_GENERATION_FAILED")
          return
        }
        this.notificationService.notify("CHANNELS.NOTIFY_GENERATION_STARTED")
      })
    })
  }

  getChannelStatusLabel(channel: TvChannel): string {
    const statusKey = this.normalizeAnalyzeStatus(channel.analyze_status)
    return this.translateService.instant(`CHANNELS.STATUS.${statusKey}`, {
      defaultValue: statusKey,
    })
  }

  shiftCalendarDay(days: number) {
    const nextDate = new Date(this.calendarDate)
    nextDate.setDate(nextDate.getDate() + days)
    this.calendarDate = nextDate
    this.scheduleCalendarRefresh()
  }

  resetCalendarDay() {
    this.calendarDate = this.getTodayDate()
    this.scheduleCalendarRefresh()
  }

  setCalendarViewMode(mode: 'grid' | 'schedule') {
    this.calendarViewMode = mode
    this.scheduleCalendarRefresh()
  }

  generateBlueprint(channel: TvChannel) {
    this.dialog.open(BlueprintGenerationDialogComponent, {
      width: '720px',
      maxWidth: '96vw',
      data: {
        channelId: channel.id,
        channelName: channel.name,
      }
    }).afterClosed().subscribe((result) => {
      if (result) {
        channel.analyze_status = 'ANALYZING'
        this.notificationService.notify("CHANNELS.NOTIFY_CHANNEL_BLUEPRINT_STARTED")
      }
    })
  }

  openGeneratePlayoutDialog(channel: TvChannel) {
    this.dialog.open(PlayoutGenerationDialogComponent, {
      width: '720px',
      maxWidth: '96vw',
      data: {channelId: channel.id}
    }).afterClosed().subscribe((result) => {
      if (result) {
        channel.analyze_status = 'ANALYZING'
        this.notificationService.notify("CHANNELS.NOTIFY_PLAYOUT_STARTED")
      }
    })
  }

  pushChannel(channel: TvChannel) {
    this.dialog.open(ConfirmationDialogComponent, {
      width: '520px',
      maxWidth: '92vw',
      data: {
        confirmationMessage: this.translateService.instant('CHANNELS.CONFIRM_PUSH', {
          name: channel.name,
        })
      }
    }).afterClosed().subscribe((confirmed) => {
      if (!confirmed) {
        return
      }
      this.isPageLoading = true
      this.tvChannelService.push(channel.id).subscribe((response) => {
        this.isPageLoading = false
        if (!response.isOk) {
          this.notificationService.notify("CHANNELS.NOTIFY_PUSH_FAILED")
          return
        }
        channel.analyze_status = 'ANALYZING'
        this.notificationService.notify("CHANNELS.NOTIFY_PUSH_STARTED")
      })
    })
  }

  openResetRulesDialog(channel: TvChannel) {
    this.dialog.open(ResetRulesDialogComponent, {
      width: '560px',
      maxWidth: '94vw',
      data: {
        channelId: channel.id,
        channelName: channel.name,
      }
    }).afterClosed().subscribe((result) => {
      if (result) {
        this.notificationService.notify("CHANNELS.NOTIFY_RULES_RESET")
        this.loadChannels()
      }
    })
  }

  openScheduleItemDetails(item: ScheduledMediaItem) {
    this.dialog.open(ScheduleMediaItemDetailDialogComponent, {
      width: '780px',
      maxWidth: '96vw',
      data: {item}
    })
  }

  trackByChannelId(_: number, channel: TvChannel) {
    return channel.id
  }

  private scheduleCalendarRefresh() {
    if (!this.showCalendarContent) {
      return
    }
    if (this.calendarRefreshHandle !== null) {
      window.clearTimeout(this.calendarRefreshHandle)
    }
    this.calendarRefreshHandle = window.setTimeout(() => {
      this.calendarRefreshHandle = null
      this.refreshCalendarEvents()
    }, 0)
  }

  private deferCalendarRendering() {
    if (this.deferredCalendarRenderHandle !== null) {
      window.cancelAnimationFrame(this.deferredCalendarRenderHandle)
    }
    this.showCalendarContent = false
    this.deferredCalendarRenderHandle = window.requestAnimationFrame(() => {
      this.deferredCalendarRenderHandle = window.requestAnimationFrame(() => {
        this.deferredCalendarRenderHandle = null
        this.showCalendarContent = true
        this.refreshCalendarEvents()
      })
    })
  }

  private refreshCalendarEvents() {
    const nextEventsByChannelId: Record<string, ChannelCalendarEvent[]> = {}
    for (const channel of this.channels) {
      nextEventsByChannelId[this.getChannelKey(channel)] = this.buildCalendarEvents(channel)
    }
    this.calendarEventsByChannelId = nextEventsByChannelId
  }

  private getChannelKey(channel: TvChannel): string {
    return String(channel.id)
  }

  private buildCalendarEvents(channel: TvChannel): ChannelCalendarEvent[] {
    return this.calendarViewMode === 'grid'
      ? this.getGridCalendarEvents(channel)
      : this.getScheduleCalendarEvents(channel)
  }

  private getScheduleCalendarEvents(channel: TvChannel): ChannelCalendarEvent[] {
    const items = channel.active_schedule_items ?? []
    const dayStart = new Date(this.calendarDate.getFullYear(), this.calendarDate.getMonth(), this.calendarDate.getDate(), 0, 0, 0, 0)
    const dayEnd = new Date(dayStart)
    dayEnd.setDate(dayEnd.getDate() + 1)

    return items
      .filter((item) => {
        const start = this.parseIsoAsWallClock(item.starts_at)
        const end = this.parseIsoAsWallClock(item.ends_at)
        return start < dayEnd && end > dayStart
      })
      .map((item) => {
        const clippedRange = this.clipRangeToDay(
          this.parseIsoAsWallClock(item.starts_at),
          this.parseIsoAsWallClock(item.ends_at),
          dayStart,
          dayEnd,
        )

        return {
          start: clippedRange.start,
          end: clippedRange.end,
          title: `${item.media_item_title} - ${this.getScheduleTimeLabel(item)}`,
          color: this.buildScheduleCalendarColor(item),
          meta: {kind: 'schedule', item},
        }
      })
  }

  private getGridCalendarEvents(channel: TvChannel): ChannelCalendarEvent[] {
    const blocks = channel.grid_data?.blocks ?? []
    const dayStart = new Date(this.calendarDate.getFullYear(), this.calendarDate.getMonth(), this.calendarDate.getDate(), 0, 0, 0, 0)
    const dayEnd = new Date(dayStart)
    dayEnd.setDate(dayEnd.getDate() + 1)
    const previousDay = new Date(dayStart)
    previousDay.setDate(previousDay.getDate() - 1)

    return blocks.flatMap((block) => {
      const occurrences = [
        this.buildBlockOccurrence(block, previousDay),
        this.buildBlockOccurrence(block, dayStart),
      ]

      return occurrences
        .filter((occurrence) => occurrence.start < dayEnd && occurrence.end > dayStart)
        .map((occurrence) => {
          const clippedRange = this.clipRangeToDay(occurrence.start, occurrence.end, dayStart, dayEnd)
          return {
            start: clippedRange.start,
            end: clippedRange.end,
            title: this.getBlockTimeLabel(block),
            color: this.buildGridCalendarColor(block),
            meta: {kind: 'block', channel, block},
          }
        })
    })
  }

  onCalendarEventClicked(event: ChannelCalendarEvent) {
    if (event.meta?.kind === 'schedule') {
      this.openScheduleItemDetails(event.meta.item)
      return
    }
    if (event.meta?.kind === 'block') {
      this.openBlockDetails(event.meta.channel, event.meta.block)
    }
  }

  openBlockDetails(channel: TvChannel, block: GridBlock) {
    if (!channel.grid_data || !channel.editorial_line_data) {
      return
    }
    this.dialog.open(GridBlockDetailDialogComponent, {
      width: '780px',
      maxWidth: '96vw',
      data: {
        block,
        grid: channel.grid_data,
        editorialLine: channel.editorial_line_data,
      }
    })
  }

  getBlockTimeLabel(block: GridBlock): string {
    return `${block.starts_at.slice(0, 5)} - ${block.ends_at.slice(0, 5)}`
  }

  getScheduleTimeLabel(item: ScheduledMediaItem): string {
    return `${this.extractTimeLabel(item.starts_at)} - ${this.extractTimeLabel(item.ends_at)}`
  }

  private buildScheduleCalendarColor(item: ScheduledMediaItem) {
    const itemKey = item.id?.toString?.() ?? `${item.media_container_id}-${item.media_item_title}`
    const seed = Array.from(itemKey).reduce((total, char) => total + char.charCodeAt(0), 0)
    const hue = (seed * 43) % 360
    return {
      primary: `hsla(${hue}, 74%, 40%, 0.92)`,
      secondary: `hsla(${hue}, 88%, 66%, 0.98)`,
    }
  }

  private buildGridCalendarColor(block: GridBlock) {
    const blockKey = block.id?.toString?.() ?? `${block.starts_at}-${block.ends_at}`
    const seed = Array.from(blockKey).reduce((total, char) => total + char.charCodeAt(0), 0)
    const hue = (seed * 37) % 360
    return {
      primary: `hsla(${hue}, 56%, 34%, 0.82)`,
      secondary: `hsla(${hue}, 74%, 72%, 0.92)`,
    }
  }

  private parseIsoAsWallClock(value: string): Date {
    const match = value.match(/^(\d{4})-(\d{2})-(\d{2})[T ](\d{2}):(\d{2})(?::(\d{2}))?/)
    if (match) {
      return new Date(
        Number(match[1]),
        Number(match[2]) - 1,
        Number(match[3]),
        Number(match[4]),
        Number(match[5]),
        Number(match[6] || 0),
        0,
      )
    }
    return new Date(value)
  }

  private clipRangeToDay(start: Date, end: Date, dayStart: Date, dayEnd: Date): {start: Date, end: Date} {
    return {
      start: start < dayStart ? new Date(dayStart) : start,
      end: end > dayEnd ? new Date(dayEnd) : end,
    }
  }

  private buildBlockOccurrence(block: GridBlock, anchorDate: Date): {start: Date, end: Date} {
    const start = this.combineDateAndTime(anchorDate, block.starts_at)
    const end = this.combineDateAndTime(anchorDate, block.ends_at)
    if (end <= start) {
      end.setDate(end.getDate() + 1)
    }
    return {start, end}
  }

  private getTodayDate(): Date {
    const now = new Date()
    return new Date(now.getFullYear(), now.getMonth(), now.getDate())
  }

  private combineDateAndTime(date: Date, time: string): Date {
    const [hours, minutes] = time.split(':').map((part) => Number(part))
    return new Date(
      date.getFullYear(),
      date.getMonth(),
      date.getDate(),
      hours,
      minutes,
      0,
      0,
    )
  }

  private extractTimeLabel(value: string): string {
    const match = value.match(/T(\d{2}:\d{2})/)
    if (match) {
      return match[1]
    }
    return value.slice(11, 16)
  }

  private normalizeAnalyzeStatus(status: string | number | null | undefined): string {
    if (typeof status === 'string') {
      return status
    }
    switch (status) {
      case 0:
        return 'IDLE'
      case 1:
        return 'ANALYZING'
      case 2:
        return 'COMPLETE'
      case 3:
        return 'SKIPPED'
      case 4:
        return 'COMPLETE_WITH_ERRORS'
      case 5:
        return 'CANCELLED'
      default:
        return String(status ?? '')
    }
  }

}
