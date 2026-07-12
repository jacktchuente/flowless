import { Component, DestroyRef, inject } from "@angular/core";
import { DatePipe, NgFor, NgIf } from "@angular/common";
import { takeUntilDestroyed } from "@angular/core/rxjs-interop";
import { Router, RouterLink } from "@angular/router";
import { TranslateModule, TranslateService } from "@ngx-translate/core";
import { Catalog } from "@project-interfaces/catalog";
import { ScheduledMediaItem, TvChannel } from "@project-interfaces/tv-channel";
import { CatalogService } from "@project-services/catalog.service";
import { TvChannelService } from "@project-services/tv-channel.service";
import { NotificationService } from "@project-shared/services/notification.service";
import { FlwDialogService } from "../../../ui/dialog.service";
import { FlwSelectComponent } from "../../../ui/select/flw-select.component";
import { FlwSegmentedComponent } from "../../../ui/segmented/flw-segmented.component";
import {
  FlwTimelineComponent,
  TimelineBlock,
} from "../../../ui/timeline/flw-timeline.component";
import { FlwMenuComponent } from "../../../ui/menu/flw-menu.component";
import { FlwIconComponent } from "../../../ui/icon/flw-icon.component";
import { categoryLegend, natureToCategory } from "../../../ui/category";
import { FlwConfirmComponent } from "../../../ui/confirm/flw-confirm.component";
import { CatalogDialogComponent } from "../catalog-dialog/catalog-dialog.component";
import { TvChannelDialogComponent } from "../tv-channel-dialog/tv-channel-dialog.component";
import { GenerationDialogComponent } from "../channel-dialogs/generation-dialog.component";
@Component({
  selector: "app-channel-management",
  standalone: true,
  imports: [
    DatePipe,
    NgFor,
    NgIf,
    RouterLink,
    TranslateModule,
    FlwSelectComponent,
    FlwSegmentedComponent,
    FlwTimelineComponent,
    FlwMenuComponent,
    FlwIconComponent,
  ],
  templateUrl: "./channel-management.component.html",
  styleUrl: "./channel-management.component.css",
})
export class ChannelManagementComponent {
  private destroyRef = inject(DestroyRef);
  catalogs: Catalog[] = [];
  channels: TvChannel[] = [];
  selectedCatalogId: string | null = null;
  calendarDate = new Date();
  calendarViewMode: "grid" | "schedule" = "grid";
  mode: "classic" | "flexible" = "classic";
  legend = categoryLegend();
  modeOptions: Array<{ label: string; value: string }> = [];
  dayOptions: Array<{ label: string; value: number }> = [];
  viewOptions: Array<{ label: string; value: string }> = [];
  constructor(
    private catalogsService: CatalogService,
    private channelsService: TvChannelService,
    private dialogs: FlwDialogService,
    private notification: NotificationService,
    private router: Router,
    private translate: TranslateService,
  ) {
    this.modeOptions = [
      { label: this.translate.instant("CHANNELS.GRID"), value: "classic" },
      {
        label: this.translate.instant("NAV.EDITORIAL_PLANNING"),
        value: "flexible",
      },
    ];
    this.dayOptions = [
      { label: this.translate.instant("CHANNELS.PREVIOUS_DAY"), value: -1 },
      { label: this.translate.instant("CHANNELS.TODAY"), value: 0 },
      { label: this.translate.instant("CHANNELS.NEXT_DAY"), value: 1 },
    ];
    this.viewOptions = [
      { label: this.translate.instant("CHANNELS.GRID"), value: "grid" },
      { label: this.translate.instant("CHANNELS.SCHEDULE"), value: "schedule" },
    ];
    catalogsService
      .getObjectBehaviorSubject()
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe((v) => {
        this.catalogs = v;
        if (!this.selectedCatalogId && v.length) {
          this.selectedCatalogId = String(v[0].id);
          this.loadChannels();
        }
      });
    channelsService
      .getObjectBehaviorSubject()
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe((v) => (this.channels = v));
  }
  get catalogOptions() {
    return this.catalogs.map((c) => ({ label: c.name, value: String(c.id) }));
  }
  get selectedCatalog() {
    return this.catalogs.find((c) => String(c.id) === this.selectedCatalogId);
  }
  onCatalog(v: unknown) {
    this.selectedCatalogId = String(v);
    this.loadChannels();
  }
  loadChannels() {
    if (this.selectedCatalogId)
      this.channelsService.listObject(
        { catalog: this.selectedCatalogId },
        true,
      );
  }
  setDay(offset: unknown) {
    const d = new Date();
    d.setDate(d.getDate() + Number(offset));
    this.calendarDate = d;
  }
  openCatalog(c?: Catalog) {
    this.dialogs.open(CatalogDialogComponent, { data: { catalog: c } });
  }
  openChannel(c?: TvChannel) {
    this.dialogs
      .open(TvChannelDialogComponent, {
        data: {
          channel: c,
          selectedCatalogId: this.selectedCatalogId,
          catalogs: this.catalogs,
        },
      })
      .closed.subscribe((ok) => {
        if (ok) this.loadChannels();
      });
  }
  openDetail(c: TvChannel) {
    this.router.navigate(["/app/channels", c.id]);
  }
  isFlexible(c: TvChannel) {
    return c.grid_data?.mode === 2;
  }
  status(c: TvChannel) {
    const counts = c.latest_generation_report?.issue_counts;
    if ((counts?.error ?? 0) > 0)
      return {
        kind: "critical",
        label: this.translate.instant("CHANNELS.ERRORS", {
          count: counts!.error,
        }),
      };
    if ((counts?.warning ?? 0) > 0)
      return {
        kind: "warning",
        label: this.translate.instant("CHANNELS.WARNINGS", {
          count: counts!.warning,
        }),
      };
    return {
      kind: "success",
      label: this.translate.instant("CHANNELS.UP_TO_DATE"),
    };
  }
  timeline(c: TvChannel): TimelineBlock[] {
    if (this.calendarViewMode === "grid")
      return (c.grid_data?.blocks ?? []).map((b) => ({
        start: b.starts_at.slice(0, 5),
        end: b.ends_at.slice(0, 5),
        title: `Bloc — ${b.allowed_categories[0] ?? "Programmation"}`,
        sub: `Priorité ${b.priority}`,
        category: natureToCategory(b.allowed_natures[0]),
      }));
    return (c.active_schedule_items ?? [])
      .filter((i) => this.sameDay(i.starts_at))
      .map((i) => ({
        start: this.time(i.starts_at),
        end: this.time(i.ends_at),
        title: i.media_item_title,
        sub: i.media_container_title,
        category: natureToCategory(i.media_nature),
      }));
  }
  generateCatalog() {
    const c = this.selectedCatalog;
    if (!c) return;
    this.dialogs
      .open(FlwConfirmComponent, {
        data: {
          title: "Générer les chaînes",
          message: this.translate.instant("CHANNELS.CONFIRM_GENERATE_CATALOG", {
            name: c.name,
          }),
          confirmLabel: "Générer",
        },
      })
      .closed.subscribe((ok) => {
        if (ok)
          this.catalogsService
            .generateChannels(c.id)
            .subscribe((r) =>
              this.notification.notify(
                r.isOk
                  ? "CHANNELS.NOTIFY_GENERATION_STARTED"
                  : "CHANNELS.NOTIFY_GENERATION_FAILED",
              ),
            );
      });
  }
  generateBlueprint(c: TvChannel) {
    this.dialogs.open(GenerationDialogComponent, {
      data: { channelId: c.id, channelName: c.name, kind: "blueprint" },
    });
  }
  generatePlayout(c: TvChannel) {
    this.dialogs.open(GenerationDialogComponent, {
      data: { channelId: c.id, channelName: c.name, kind: "playout" },
    });
  }
  push(c: TvChannel) {
    this.channelsService
      .push(c.id)
      .subscribe((r) =>
        this.notification.notify(
          r.isOk
            ? "CHANNELS.NOTIFY_PUSH_STARTED"
            : "CHANNELS.NOTIFY_PUSH_FAILED",
        ),
      );
  }
  remove(c: TvChannel) {
    this.dialogs
      .open(FlwConfirmComponent, {
        data: {
          title: "Supprimer la chaîne",
          message: `Supprimer « ${c.name} » ?`,
          confirmLabel: "Supprimer",
        },
      })
      .closed.subscribe((ok) => {
        if (ok)
          this.channelsService
            .deleteObject(String(c.id))
            .subscribe(() => this.loadChannels());
      });
  }
  private sameDay(value: string) {
    const d = new Date(value);
    return (
      d.getFullYear() === this.calendarDate.getFullYear() &&
      d.getMonth() === this.calendarDate.getMonth() &&
      d.getDate() === this.calendarDate.getDate()
    );
  }
  private time(value: string) {
    return new Date(value).toLocaleTimeString("fr-FR", {
      hour: "2-digit",
      minute: "2-digit",
      hour12: false,
    });
  }
}
