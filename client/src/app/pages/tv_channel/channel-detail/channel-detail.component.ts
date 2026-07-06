import {Component, DestroyRef, ElementRef, ViewChild, inject} from '@angular/core';
import {DatePipe, NgClass, NgFor, NgIf} from "@angular/common";
import {ActivatedRoute, Router, RouterLink} from "@angular/router";
import {MatButtonModule} from "@angular/material/button";
import {MatDialog} from "@angular/material/dialog";
import {MatIconModule} from "@angular/material/icon";
import {MatMenuModule} from "@angular/material/menu";
import {MatProgressSpinnerModule} from "@angular/material/progress-spinner";
import {filter} from "rxjs/operators";
import {CalendarEvent, CalendarModule} from "angular-calendar";
import {WebsocketService} from "@kwyxyz/ngx-request";
import {takeUntilDestroyed} from "@angular/core/rxjs-interop";
import {TranslateModule, TranslateService} from "@ngx-translate/core";
import {EditorialLineData, GridBlock, ScheduledMediaItem, TvChannel} from "@project-interfaces/tv-channel";
import {TvChannelLogoPromptResponse, TvChannelService} from "@project-services/tv-channel.service";
import {ConfirmationDialogComponent} from "@project-shared/confirmation-dialog/confirmation-dialog.component";
import {NotificationService} from "@project-shared/services/notification.service";
import {BlueprintGenerationDialogComponent} from "../blueprint-generation-dialog/blueprint-generation-dialog.component";
import {EditorialLineDetailDialogComponent} from "../editorial-line-detail-dialog/editorial-line-detail-dialog.component";
import {GridBlockDetailDialogComponent} from "../grid-block-detail-dialog/grid-block-detail-dialog.component";
import {GenerationReportDialogComponent} from "../generation-report-dialog/generation-report-dialog.component";
import {PlayoutGenerationDialogComponent} from "../playout-generation-dialog/playout-generation-dialog.component";
import {ResetRulesDialogComponent} from "../reset-rules-dialog/reset-rules-dialog.component";
import {ScheduleMediaItemDetailDialogComponent} from "../schedule-media-item-detail-dialog/schedule-media-item-detail-dialog.component";
import {TvChannelDialogComponent} from "../tv-channel-dialog/tv-channel-dialog.component";

type ChannelCalendarEventMeta =
  | {kind: 'schedule', item: ScheduledMediaItem}
  | {kind: 'block', block: GridBlock}

type ChannelCalendarEvent = CalendarEvent<ChannelCalendarEventMeta>

@Component({
  selector: 'app-channel-detail',
  standalone: true,
  imports: [
    RouterLink,
    DatePipe,
    MatButtonModule,
    MatIconModule,
    MatMenuModule,
    MatProgressSpinnerModule,
    TranslateModule,
    NgClass,
    NgFor,
    NgIf,
    CalendarModule,
  ],
  templateUrl: './channel-detail.component.html',
  styleUrl: './channel-detail.component.css'
})
export class ChannelDetailComponent {
  private readonly destroyRef = inject(DestroyRef)
  @ViewChild('logoUploadInput') private logoUploadInput?: ElementRef<HTMLInputElement>

  channel: TvChannel | null = null
  isLoading = true
  isPageLoading = false
  logoLoadFailed = false
  calendarDate = new Date()
  scheduleCalendarEvents: ChannelCalendarEvent[] = []
  gridCalendarEvents: ChannelCalendarEvent[] = []

  constructor(
    private route: ActivatedRoute,
    private router: Router,
    private tvChannelService: TvChannelService,
    private websocketService: WebsocketService,
    private notificationService: NotificationService,
    private dialog: MatDialog,
    private translateService: TranslateService,
  ) {
    this.route.paramMap
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe((params) => {
        const channelId = params.get('channelId')
        if (!channelId) {
          this.router.navigate(['/app/channels'])
          return
        }
        this.loadChannel(channelId)
      })

    this.websocketService.crudEvent
      .pipe(
        filter((event: any) => event.type?.toLowerCase?.() === 'tvchannel'),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe((event: any) => {
        const currentId = this.channel?.id?.toString()
        if (!currentId) {
          return
        }
        if (event.id?.toString?.() !== currentId) {
          return
        }
        if (event.action === 'destroy') {
          this.router.navigate(['/app/channels'])
          return
        }
        this.loadChannel(currentId)
      })
  }

  get editorialLine(): EditorialLineData | null {
    return this.channel?.editorial_line_data ?? null
  }

  get isFlexibleChannel(): boolean {
    return this.channel?.grid_data?.mode === 2
  }

  loadChannel(channelId: string) {
    this.isLoading = true
    this.tvChannelService.getDetail(channelId).subscribe((response) => {
      this.isLoading = false
      if (!response.isOk) {
        this.isPageLoading = false
        this.notificationService.notify("CHANNEL_DETAIL.NOTIFY_LOAD_FAILED")
        return
      }
      this.channel = response.body as TvChannel
      this.logoLoadFailed = false
      this.calendarDate = this.getTodayDate()
      this.refreshCalendarData()
      this.isPageLoading = false
    })
  }

  get reportIssueCount(): number {
    const counts = this.channel?.latest_generation_report?.issue_counts
    if (!counts) {
      return 0
    }
    return counts.error + counts.warning
  }

  get reportBadgeClass(): string {
    const counts = this.channel?.latest_generation_report?.issue_counts
    if (counts?.error) {
      return 'report-badge-error'
    }
    if (counts?.warning) {
      return 'report-badge-warning'
    }
    return ''
  }

  openGenerationReportsDialog() {
    if (!this.channel) {
      return
    }
    this.dialog.open(GenerationReportDialogComponent, {
      width: '760px',
      maxWidth: '96vw',
      data: {
        channelId: this.channel.id,
        channelName: this.channel.name,
      },
    })
  }

  openEditChannelDialog() {
    if (!this.channel) {
      return
    }
    this.dialog.open(TvChannelDialogComponent, {
      width: '720px',
      maxWidth: '96vw',
      data: {
        channel: this.channel,
        selectedCatalogId: this.channel.catalog?.toString?.() ?? null,
        catalogs: [{
          id: this.channel.catalog,
          name: this.channel.catalog_name,
          description: '',
        }],
      }
    }).afterClosed().subscribe((result) => {
      if (result && this.channel) {
        this.loadChannel(this.channel.id.toString())
      }
    })
  }

  generateBlueprint() {
    if (!this.channel) {
      return
    }
    this.dialog.open(BlueprintGenerationDialogComponent, {
      width: '720px',
      maxWidth: '96vw',
      data: {
        channelId: this.channel.id,
        channelName: this.channel.name,
      }
    }).afterClosed().subscribe((result) => {
      if (result && this.channel) {
        this.channel.analyze_status = 'ANALYZING'
        this.notificationService.notify("CHANNEL_DETAIL.NOTIFY_BLUEPRINT_STARTED")
      }
    })
  }

  openGeneratePlayoutDialog() {
    if (!this.channel) {
      return
    }
    this.dialog.open(PlayoutGenerationDialogComponent, {
      width: '720px',
      maxWidth: '96vw',
      data: {channelId: this.channel.id}
    }).afterClosed().subscribe((result) => {
      if (result && this.channel) {
        this.channel.analyze_status = 'ANALYZING'
        this.notificationService.notify("CHANNEL_DETAIL.NOTIFY_PLAYOUT_STARTED")
      }
    })
  }

  pushChannel() {
    if (!this.channel) {
      return
    }
    this.dialog.open(ConfirmationDialogComponent, {
      width: '520px',
      maxWidth: '92vw',
      data: {
        confirmationMessage: this.translateService.instant('CHANNEL_DETAIL.CONFIRM_PUSH', {name: this.channel.name})
      }
    }).afterClosed().subscribe((confirmed) => {
      if (!confirmed || !this.channel) {
        return
      }
      this.isPageLoading = true
      this.tvChannelService.push(this.channel.id).subscribe((response) => {
        this.isPageLoading = false
        if (!response.isOk) {
          this.notificationService.notify("CHANNEL_DETAIL.NOTIFY_PUSH_FAILED")
          return
        }
        this.channel!.analyze_status = 'ANALYZING'
        this.notificationService.notify("CHANNEL_DETAIL.NOTIFY_PUSH_STARTED")
      })
    })
  }

  triggerLogoUpload() {
    this.logoUploadInput?.nativeElement.click()
  }

  onLogoSelected(event: Event) {
    if (!this.channel) {
      return
    }
    const input = event.target as HTMLInputElement | null
    const file = input?.files?.[0]
    if (!file) {
      return
    }
    this.isPageLoading = true
    this.tvChannelService.uploadLogo(this.channel.id, file).subscribe((response) => {
      if (input) {
        input.value = ''
      }
      if (!response.isOk) {
        this.isPageLoading = false
        this.notificationService.notify("CHANNEL_DETAIL.NOTIFY_LOGO_UPLOAD_FAILED")
        return
      }
      this.notificationService.notify("CHANNEL_DETAIL.NOTIFY_LOGO_UPDATED")
      this.loadChannel(this.channel!.id.toString())
    })
  }

  generateLogo(backend: 'comfyui' | 'openai') {
    if (!this.channel) {
      return
    }
    this.tvChannelService.generateLogo(this.channel.id, backend)
      .subscribe((response) => {
        if (!response.isOk) {
          this.notificationService.notify("CHANNEL_DETAIL.NOTIFY_LOGO_GENERATION_FAILED")
          return
        }
        this.logoLoadFailed = false
        this.notificationService.notify("CHANNEL_DETAIL.NOTIFY_LOGO_GENERATION_STARTED")
      })
  }

  downloadLogoPrompt() {
    if (!this.channel) {
      return
    }
    this.isPageLoading = true
    this.tvChannelService.exportLogoPrompt(this.channel.id).subscribe((response) => {
      this.isPageLoading = false
      if (!response.isOk) {
        this.notificationService.notify("CHANNEL_DETAIL.NOTIFY_LOGO_PROMPT_FAILED")
        return
      }
      const body = response.body as TvChannelLogoPromptResponse
      const prompt = body?.prompt ?? ''
      const safeName = this.channel!.name
        .toLowerCase()
        .replace(/[^a-z0-9]+/g, '-')
        .replace(/^-+|-+$/g, '') || `channel-${this.channel!.id}`
      const blob = new Blob([prompt], {type: 'text/plain;charset=utf-8'})
      const url = URL.createObjectURL(blob)
      const anchor = document.createElement('a')
      anchor.href = url
      anchor.download = `${safeName}-logo-prompt.txt`
      anchor.click()
      URL.revokeObjectURL(url)
      this.notificationService.notify("CHANNEL_DETAIL.NOTIFY_LOGO_PROMPT_DOWNLOADED")
    })
  }

  openResetRulesDialog() {
    if (!this.channel) {
      return
    }
    this.dialog.open(ResetRulesDialogComponent, {
      width: '560px',
      maxWidth: '94vw',
      data: {
        channelId: this.channel.id,
        channelName: this.channel.name,
      }
    }).afterClosed().subscribe((result) => {
      if (result && this.channel) {
        this.isPageLoading = true
        this.notificationService.notify("CHANNEL_DETAIL.NOTIFY_RULES_RESET")
        this.loadChannel(this.channel.id.toString())
      }
    })
  }

  getChannelStatusLabel(): string {
    const statusKey = this.normalizeAnalyzeStatus(this.channel?.analyze_status)
    return this.translateService.instant(`COMMON.STATUS.${statusKey}`, {
      defaultValue: statusKey,
    })
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

  openEditorialLineDetailDialog() {
    if (!this.channel || !this.editorialLine) {
      return
    }
    this.dialog.open(EditorialLineDetailDialogComponent, {
      width: '860px',
      maxWidth: '96vw',
      data: {
        channelName: this.channel.name,
        editorialLine: this.editorialLine,
      }
    })
  }

  openBlockDetails(block: GridBlock) {
    if (!this.channel?.grid_data || !this.channel.editorial_line_data) {
      return
    }
    this.dialog.open(GridBlockDetailDialogComponent, {
      width: '780px',
      maxWidth: '96vw',
      data: {
        block,
        grid: this.channel.grid_data,
        editorialLine: this.channel.editorial_line_data,
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

  shiftCalendarDay(days: number) {
    const nextDate = new Date(this.calendarDate)
    nextDate.setDate(nextDate.getDate() + days)
    this.calendarDate = nextDate
    this.refreshCalendarData()
  }

  resetCalendarDay() {
    this.calendarDate = this.getTodayDate()
    this.refreshCalendarData()
  }

  onCalendarEventClicked(event: ChannelCalendarEvent) {
    if (event.meta?.kind === 'schedule') {
      this.openScheduleItemDetails(event.meta.item)
      return
    }
    if (event.meta?.kind === 'block') {
      this.openBlockDetails(event.meta.block)
    }
  }

  getBlockTimeLabel(block: GridBlock): string {
    return `${block.starts_at.slice(0, 5)} - ${block.ends_at.slice(0, 5)}`
  }

  getScheduleTimeLabel(item: ScheduledMediaItem): string {
    return `${this.extractTimeLabel(item.starts_at)} - ${this.extractTimeLabel(item.ends_at)}`
  }

  private refreshCalendarData() {
    const dayBounds = this.getCalendarDayBounds()
    this.scheduleCalendarEvents = this.buildScheduleCalendarEvents(dayBounds.dayStart, dayBounds.dayEnd)
    this.gridCalendarEvents = this.buildGridCalendarEvents(dayBounds.dayStart, dayBounds.dayEnd)
  }

  private buildScheduleCalendarEvents(dayStart: Date, dayEnd: Date): ChannelCalendarEvent[] {
    const items = this.channel?.active_schedule_items ?? []
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

        const isInterstitial = this.isInterstitialItem(item)
        const titlePrefix = isInterstitial ? `▸ ${item.role_label ?? 'interlude'} · ` : ''

        return {
          start: clippedRange.start,
          end: clippedRange.end,
        title: `${titlePrefix}${item.media_item_title} · ${item.block_name} · ${this.getScheduleTimeLabel(item)}`,
        color: this.buildScheduleCalendarColor(item),
        meta: {kind: 'schedule', item},
        }
      })
  }

  private isInterstitialItem(item: ScheduledMediaItem): boolean {
    return item.parent_schedule_item !== null && item.parent_schedule_item !== undefined
  }

  private buildGridCalendarEvents(dayStart: Date, dayEnd: Date): ChannelCalendarEvent[] {
    const blocks = this.channel?.grid_data?.blocks ?? []
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
            meta: {kind: 'block', block},
          }
        })
    })
  }

  private buildScheduleCalendarColor(item: ScheduledMediaItem) {
    if (this.isInterstitialItem(item)) {
      return {
        primary: 'hsla(0, 0%, 42%, 0.85)',
        secondary: 'hsla(0, 0%, 68%, 0.9)',
      }
    }
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

  private buildBlockOccurrence(block: GridBlock, anchorDate: Date): {start: Date, end: Date} {
    const start = this.combineDateAndTime(anchorDate, block.starts_at)
    const end = this.combineDateAndTime(anchorDate, block.ends_at)
    if (end <= start) {
      end.setDate(end.getDate() + 1)
    }
    return {start, end}
  }

  private clipRangeToDay(start: Date, end: Date, dayStart: Date, dayEnd: Date): {start: Date, end: Date} {
    return {
      start: start < dayStart ? new Date(dayStart) : start,
      end: end > dayEnd ? new Date(dayEnd) : end,
    }
  }

  private getCalendarDayBounds(): {dayStart: Date, dayEnd: Date} {
    const dayStart = new Date(this.calendarDate.getFullYear(), this.calendarDate.getMonth(), this.calendarDate.getDate(), 0, 0, 0, 0)
    const dayEnd = new Date(dayStart)
    dayEnd.setDate(dayEnd.getDate() + 1)
    return {dayStart, dayEnd}
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

}
