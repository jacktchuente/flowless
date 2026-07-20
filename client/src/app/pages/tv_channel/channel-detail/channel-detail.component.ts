import {
  Component,
  DestroyRef,
  ElementRef,
  ViewChild,
  inject,
} from "@angular/core";
import { DatePipe, NgClass, NgFor, NgIf } from "@angular/common";
import { ActivatedRoute, Router, RouterLink } from "@angular/router";
import { filter } from "rxjs";
import { takeUntilDestroyed } from "@angular/core/rxjs-interop";
import { WebsocketService } from "@kwyxyz/ngx-request";
import {
  EditorialLineData,
  GridBlock,
  FormOptions,
  GRID_MODE_FLEXIBLE,
  GRID_MODE_MARATHON,
  MarathonKindPolicy,
  PlayoutGenerationReport,
  PROGRAMMING_MODE_MARATHON,
  RuleValuesByAxis,
  ScheduledMediaItem,
  TvChannel,
} from "@project-interfaces/tv-channel";
import { TvChannelService } from "@project-services/tv-channel.service";
import { NotificationService } from "@project-shared/services/notification.service";
import { FlwDialogService } from "../../../ui/dialog.service";
import { FlwIconComponent } from "../../../ui/icon/flw-icon.component";
import { FlwSegmentedComponent } from "../../../ui/segmented/flw-segmented.component";
import {
  FlwTimelineComponent,
  TimelineBlock,
} from "../../../ui/timeline/flw-timeline.component";
import { TimeAgoPipe } from "../../../ui/pipes/time-ago.pipe";
import { FlwConfirmComponent } from "../../../ui/confirm/flw-confirm.component";
import {
  containerKindLabel,
  natureLabel,
  natureToCategory,
} from "../../../ui/category";
import { TvChannelDialogComponent } from "../tv-channel-dialog/tv-channel-dialog.component";
import { GenerationDialogComponent } from "../channel-dialogs/generation-dialog.component";
import { LogoDialogComponent } from "../channel-dialogs/logo-dialog.component";
import { ReportDialogComponent } from "../channel-dialogs/report-dialog.component";
import { ResetRulesDialogComponent } from "../channel-dialogs/reset-rules-dialog.component";
import { ScheduleDetailDialogComponent } from "../channel-dialogs/schedule-detail-dialog.component";
import { GridSettingsDialogComponent } from "../channel-dialogs/grid-settings-dialog.component";
import { MarathonConfigDialogComponent } from "../channel-dialogs/marathon-config-dialog.component";
import { EditorialLineDialogComponent } from "../channel-dialogs/editorial-line-dialog.component";
import { GridBlockDialogComponent } from "../channel-dialogs/grid-block-dialog.component";
import { TranslateModule, TranslateService } from "@ngx-translate/core";
@Component({
  selector: "app-channel-detail",
  standalone: true,
  imports: [
    DatePipe,
    NgClass,
    NgFor,
    NgIf,
    RouterLink,
    FlwIconComponent,
    FlwSegmentedComponent,
    FlwTimelineComponent,
    TimeAgoPipe,
    TranslateModule,
  ],
  templateUrl: "./channel-detail.component.html",
  styleUrl: "./channel-detail.component.css",
})
export class ChannelDetailComponent {
  private destroyRef = inject(DestroyRef);
  @ViewChild("file") file?: ElementRef<HTMLInputElement>;
  channel: TvChannel | null = null;
  isLoading = true;
  calendarDate = new Date();
  dayOffset = 0;
  gridWarnings: string[] = [];
  formOptions: FormOptions | null = null;
  reportCount = 0;
  dayOptions: Array<{ label: string; value: number }> = [];
  constructor(
    route: ActivatedRoute,
    private router: Router,
    private service: TvChannelService,
    ws: WebsocketService,
    private notification: NotificationService,
    private dialogs: FlwDialogService,
    private translate: TranslateService,
  ) {
    route.paramMap.pipe(takeUntilDestroyed(this.destroyRef)).subscribe((p) => {
      const id = p.get("channelId");
      if (id) this.load(id);
      else router.navigate(["/app/channels"]);
    });
    ws.crudEvent
      .pipe(
        filter((e: any) => e.type?.toLowerCase?.() === "tvchannel"),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe((e: any) => {
        if (String(e.id) === String(this.channel?.id)) this.load(String(e.id));
      });
    this.dayOptions = [
      { label: this.translate.instant("CHANNELS.PREVIOUS_DAY"), value: -1 },
      { label: this.translate.instant("CHANNELS.TODAY"), value: 0 },
      { label: this.translate.instant("CHANNELS.NEXT_DAY"), value: 1 },
    ];
  }
  get isFlexible() {
    return this.channel?.grid_data?.mode === GRID_MODE_FLEXIBLE;
  }
  get isMarathon() {
    // Avant le premier blueprint la chaine marathon n'a pas encore de grille:
    // le mode de programmation fait foi.
    return (
      this.channel?.grid_data?.mode === GRID_MODE_MARATHON ||
      (this.channel?.programming_mode === PROGRAMMING_MODE_MARATHON &&
        !this.channel?.grid_data)
    );
  }
  get hasMarathonGrid() {
    return this.channel?.grid_data?.mode === GRID_MODE_MARATHON;
  }
  get hasBlockGrid() {
    return !this.isFlexible && !this.isMarathon;
  }
  get marathonPolicies(): MarathonKindPolicy[] {
    return this.channel?.grid_data?.marathon_config?.kind_policies ?? [];
  }
  get gridRows(): Array<{
    block?: GridBlock;
    gap?: { starts_at: string; ends_at: string };
  }> {
    const blocks = [...(this.channel?.grid_data?.blocks ?? [])].sort((a, b) =>
      a.starts_at.localeCompare(b.starts_at),
    );
    const rows: Array<{
      block?: GridBlock;
      gap?: { starts_at: string; ends_at: string };
    }> = [];
    blocks.forEach((block, index) => {
      rows.push({ block });
      const next = blocks[index + 1];
      if (next && block.ends_at.slice(0, 5) < next.starts_at.slice(0, 5))
        rows.push({
          gap: {
            starts_at: block.ends_at.slice(0, 5),
            ends_at: next.starts_at.slice(0, 5),
          },
        });
    });
    return rows;
  }
  get otherWarnings() {
    // Les trous entre blocs sont déjà rendus en lignes riches intercalées.
    return this.gridWarnings.filter((w) => !w.startsWith("Gap between blocks"));
  }
  lineRules(line: EditorialLineData) {
    const tags = (rules: RuleValuesByAxis | undefined) => [
      ...(rules?.categories ?? []),
      ...(rules?.genres ?? []).map((value) =>
        this.translate.instant("CHANNEL_DIALOGS.COMMON.GENRE_VALUE", { value }),
      ),
      ...(rules?.tags ?? []).map((value) =>
        this.translate.instant("CHANNEL_DIALOGS.COMMON.TAG_VALUE", { value }),
      ),
      ...(rules?.natures ?? []).map((v) => this.translate.instant(natureLabel(v))),
      ...(rules?.container_kinds ?? []).map((v) =>
        this.translate.instant(containerKindLabel(v)),
      ),
    ];
    return [
      {
        label: "CHANNEL_DETAIL.ALLOWED",
        kind: "allow",
        tags: tags(line.allowed),
      },
      {
        label: "CHANNEL_DETAIL.PREFERRED",
        kind: "prefer",
        tags: tags(line.preferred),
      },
      {
        label: "CHANNEL_DETAIL.FORBIDDEN",
        kind: "forbid",
        tags: tags(line.forbidden),
      },
    ].filter((rule) => rule.tags.length);
  }
  status() {
    const c = this.channel?.latest_generation_report?.issue_counts;
    if ((c?.error ?? 0) > 0)
      return {
        kind: "critical",
        label: this.translate.instant("CHANNELS.ERRORS", { count: c!.error }),
      };
    if ((c?.warning ?? 0) > 0)
      return {
        kind: "warning",
        label: this.translate.instant("CHANNELS.WARNINGS", {
          count: c!.warning,
        }),
      };
    return {
      kind: "success",
      label: this.translate.instant("CHANNELS.UP_TO_DATE"),
    };
  }
  load(id: string) {
    this.isLoading = true;
    this.service.getDetail(id).subscribe((r) => {
      this.isLoading = false;
      if (!r.isOk) {
        this.notification.notify("CHANNEL_DETAIL.NOTIFY_LOAD_FAILED");
        return;
      }
      this.channel = r.body as TvChannel;
      this.service
        .getGridWarnings(id)
        .subscribe(
          (w) => (this.gridWarnings = w.isOk ? (w.body as any).warnings : []),
        );
      this.service.getGenerationReports(id).subscribe((r2) => {
        const reports = r2.body as PlayoutGenerationReport[] | null;
        this.reportCount =
          r2.isOk && Array.isArray(reports) ? reports.length : 0;
      });
    });
  }
  edit() {
    if (!this.channel) return;
    this.dialogs
      .open(TvChannelDialogComponent, {
        data: {
          channel: this.channel,
          selectedCatalogId: String(this.channel.catalog),
          catalogs: [
            {
              id: this.channel.catalog,
              name: this.channel.catalog_name,
              description: null,
            },
          ],
        },
      })
      .closed.subscribe((ok) => {
        if (ok) this.load(String(this.channel!.id));
      });
  }
  generateBlueprint() {
    if (!this.channel) return;
    this.openGeneration("blueprint");
  }
  generatePlayout() {
    if (!this.channel) return;
    this.openGeneration("playout");
  }
  private openGeneration(kind: "blueprint" | "playout") {
    this.dialogs.open(GenerationDialogComponent, {
      data: {
        channelId: this.channel!.id,
        channelName: this.channel!.name,
        kind,
        isMarathon: this.isMarathon,
      },
    });
  }
  push() {
    if (!this.channel) return;
    this.service
      .push(this.channel.id)
      .subscribe((r) =>
        this.notification.notify(
          r.isOk
            ? "CHANNEL_DETAIL.NOTIFY_PUSH_STARTED"
            : "CHANNEL_DETAIL.NOTIFY_PUSH_FAILED",
        ),
      );
  }
  newVersion() {
    if (!this.channel) return;
    this.dialogs
      .open(FlwConfirmComponent, {
        data: {
          title: this.translate.instant("MANUAL_EDIT.NEW_VERSION"),
          message: this.translate.instant("MANUAL_EDIT.CONFIRM_NEW_VERSION"),
          confirmLabel: this.translate.instant("MANUAL_EDIT.CREATE"),
        },
      })
      .closed.subscribe((ok) => {
        if (ok)
          this.service
            .createGridVersion(this.channel!.id)
            .subscribe(() => this.load(String(this.channel!.id)));
      });
  }
  upload(e: Event) {
    const f = (e.target as HTMLInputElement).files?.[0];
    if (f && this.channel)
      this.service.uploadLogo(this.channel.id, f).subscribe((r) => {
        if (r.isOk) this.load(String(this.channel!.id));
      });
  }
  generateLogo(backend: "comfyui" | "openai") {
    if (this.channel)
      this.service
        .generateLogo(this.channel.id, backend)
        .subscribe((r) =>
          this.notification.notify(
            r.isOk
              ? "CHANNEL_DETAIL.NOTIFY_LOGO_GENERATION_STARTED"
              : "CHANNEL_DETAIL.NOTIFY_LOGO_GENERATION_FAILED",
          ),
        );
  }
  openLogoDialog() {
    if (!this.channel) return;
    this.dialogs
      .open(LogoDialogComponent, {
        data: {
          channelId: this.channel.id,
          channelName: this.channel.name,
          logo: this.channel.logo ?? null,
        },
      })
      .closed.subscribe((changed) => {
        if (changed) this.load(String(this.channel!.id));
      });
  }
  openReports() {
    if (this.channel)
      this.dialogs.open(ReportDialogComponent, {
        data: { channelId: this.channel.id, channelName: this.channel.name },
      });
  }
  openResetRules() {
    if (!this.channel) return;
    this.dialogs
      .open(ResetRulesDialogComponent, {
        data: { channelId: this.channel.id, channelName: this.channel.name },
      })
      .closed.subscribe((saved) => {
        if (saved) this.load(String(this.channel!.id));
      });
  }
  openEditorialLine() {
    if (!this.channel) return;
    // Sans ligne existante, le dialogue part de valeurs par defaut: le PUT
    // editorial-line fait un get_or_create cote API — pas besoin de passer
    // par le blueprint pour creer la ligne.
    const line: EditorialLineData = this.channel.editorial_line_data ?? {
      allowed: {},
      preferred: {},
      forbidden: {},
      start_at: "06:00:00",
      end_at: "22:00:00",
      allow_filler: true,
    };
    this.withFormOptions((options) =>
      this.dialogs
        .open(EditorialLineDialogComponent, {
          data: {
            channelId: this.channel!.id,
            line,
            formOptions: options,
          },
        })
        .closed.subscribe((saved) => {
          if (saved) this.load(String(this.channel!.id));
        }),
    );
  }
  openMarathonConfig() {
    if (!this.channel?.grid_data) return;
    this.withFormOptions((options) =>
      this.dialogs
        .open(MarathonConfigDialogComponent, {
          data: {
            channelId: this.channel!.id,
            policies: this.marathonPolicies,
            formOptions: options,
          },
        })
        .closed.subscribe((saved) => {
          if (saved) this.load(String(this.channel!.id));
        }),
    );
  }
  marathonPolicyLabel(policy: MarathonKindPolicy) {
    return this.translate.instant(containerKindLabel(policy.container_kind));
  }
  openGridSettings() {
    if (!this.channel?.grid_data) return;
    this.withFormOptions((options) =>
      this.dialogs
        .open(GridSettingsDialogComponent, {
          data: {
            channelId: this.channel!.id,
            policy: this.channel!.grid_data!.post_filler_policy,
            formOptions: options,
          },
        })
        .closed.subscribe((saved) => {
          if (saved) this.load(String(this.channel!.id));
        }),
    );
  }
  openBlock(
    block: GridBlock | null,
    defaults?: { starts_at: string; ends_at: string },
  ) {
    if (!this.channel?.grid_data) return;
    this.withFormOptions((options) =>
      this.dialogs
        .open(GridBlockDialogComponent, {
          data: {
            channelId: this.channel!.id,
            channelName: this.channel!.name,
            gridLayoutId: this.channel!.grid_data!.id,
            block,
            defaults,
            formOptions: options,
          },
        })
        .closed.subscribe((saved) => {
          if (saved) this.load(String(this.channel!.id));
        }),
    );
  }
  openScheduleBlock(block: TimelineBlock) {
    const item = this.channel?.active_schedule_items.find(
      (candidate) =>
        candidate.media_item_title === block.title &&
        this.time(candidate.starts_at) === block.start,
    );
    if (item)
      this.dialogs.open(ScheduleDetailDialogComponent, { data: { item } });
  }
  private withFormOptions(callback: (options: FormOptions) => void) {
    if (this.formOptions) {
      callback(this.formOptions);
      return;
    }
    this.service.getFormOptions().subscribe((response) => {
      if (response.isOk) {
        this.formOptions = response.body as FormOptions;
        callback(this.formOptions);
      }
    });
  }
  gridBlocks(): TimelineBlock[] {
    return (this.channel?.grid_data?.blocks ?? []).map((b) => ({
      start: b.starts_at.slice(0, 5),
      end: b.ends_at.slice(0, 5),
      title: this.translate.instant("CHANNEL_DETAIL.BLOCK_TITLE", {
        category:
          b.allowed?.categories?.[0] ??
          b.allowed?.genres?.[0] ??
          b.allowed?.tags?.[0] ??
          this.translate.instant("CHANNEL_DETAIL.PROGRAMMING"),
      }),
      sub: this.translate.instant("CHANNEL_DETAIL.BLOCK_PRIORITY", {
        priority: b.priority,
      }),
      category: natureToCategory(b.allowed?.natures?.[0] ?? null),
    }));
  }
  scheduleBlocks(): TimelineBlock[] {
    return (this.channel?.active_schedule_items ?? [])
      .filter((i) => this.sameDay(i.starts_at))
      .map((i) => ({
        start: this.time(i.starts_at),
        end: this.time(i.ends_at),
        title: i.media_item_title,
        sub: i.media_container_title,
        category: natureToCategory(i.media_nature),
      }));
  }
  blockTags(b: GridBlock) {
    return [
      ...(b.allowed?.categories ?? []),
      ...(b.allowed?.genres ?? []).map((value) =>
        this.translate.instant("CHANNEL_DIALOGS.COMMON.GENRE_VALUE", { value }),
      ),
      ...(b.allowed?.tags ?? []).map((value) =>
        this.translate.instant("CHANNEL_DIALOGS.COMMON.TAG_VALUE", { value }),
      ),
      ...(b.allowed?.natures ?? []).map((value) =>
        this.translate.instant(natureLabel(value)),
      ),
      ...(b.allowed?.container_kinds ?? []).map((value) =>
        this.translate.instant(containerKindLabel(value)),
      ),
    ].slice(0, 4);
  }
  setDay(offset: unknown) {
    this.dayOffset = Number(offset);
    const next = new Date();
    next.setDate(next.getDate() + this.dayOffset);
    this.calendarDate = next;
  }
  private sameDay(v: string) {
    const d = new Date(v);
    return d.toDateString() === this.calendarDate.toDateString();
  }
  private time(v: string) {
    return new Date(v).toLocaleTimeString("fr-FR", {
      hour: "2-digit",
      minute: "2-digit",
      hour12: false,
    });
  }
}
