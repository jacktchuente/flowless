import {
  Component,
  DestroyRef,
  ElementRef,
  ViewChild,
  inject,
} from "@angular/core";
import { DatePipe, NgFor, NgIf } from "@angular/common";
import { ActivatedRoute, Router, RouterLink } from "@angular/router";
import { filter } from "rxjs";
import { takeUntilDestroyed } from "@angular/core/rxjs-interop";
import { WebsocketService } from "@kwyxyz/ngx-request";
import {
  GridBlock,
  ScheduledMediaItem,
  TvChannel,
} from "@project-interfaces/tv-channel";
import { TvChannelService } from "@project-services/tv-channel.service";
import { NotificationService } from "@project-shared/services/notification.service";
import { FlwDialogService } from "../../../ui/dialog.service";
import { FlwIconComponent } from "../../../ui/icon/flw-icon.component";
import {
  FlwTimelineComponent,
  TimelineBlock,
} from "../../../ui/timeline/flw-timeline.component";
import { TimeAgoPipe } from "../../../ui/pipes/time-ago.pipe";
import { FlwConfirmComponent } from "../../../ui/confirm/flw-confirm.component";
import { natureToCategory } from "../../../ui/category";
import { TvChannelDialogComponent } from "../tv-channel-dialog/tv-channel-dialog.component";
@Component({
  selector: "app-channel-detail",
  standalone: true,
  imports: [
    DatePipe,
    NgFor,
    NgIf,
    RouterLink,
    FlwIconComponent,
    FlwTimelineComponent,
    TimeAgoPipe,
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
  gridWarnings: string[] = [];
  constructor(
    route: ActivatedRoute,
    private router: Router,
    private service: TvChannelService,
    ws: WebsocketService,
    private notification: NotificationService,
    private dialogs: FlwDialogService,
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
  }
  get isFlexible() {
    return this.channel?.grid_data?.mode === 2;
  }
  get reportIssueCount() {
    const c = this.channel?.latest_generation_report?.issue_counts;
    return (c?.error ?? 0) + (c?.warning ?? 0);
  }
  status() {
    const c = this.channel?.latest_generation_report?.issue_counts;
    if ((c?.error ?? 0) > 0)
      return { kind: "critical", label: `${c!.error} erreurs` };
    if ((c?.warning ?? 0) > 0)
      return { kind: "warning", label: `${c!.warning} alertes` };
    return { kind: "success", label: "À jour" };
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
    this.service
      .generateBlueprint(this.channel.id, {
        grid_generation_mode: "preset_and_llm",
        grid_only: false,
        reboot: false,
      })
      .subscribe((r) =>
        this.notification.notify(
          r.isOk
            ? "CHANNEL_DETAIL.NOTIFY_BLUEPRINT_STARTED"
            : "CHANNELS.NOTIFY_GENERATION_FAILED",
        ),
      );
  }
  generatePlayout() {
    if (!this.channel) return;
    this.service
      .generatePlayout(this.channel.id, { days: 7, reset: false })
      .subscribe((r) =>
        this.notification.notify(
          r.isOk
            ? "CHANNEL_DETAIL.NOTIFY_PLAYOUT_STARTED"
            : "CHANNELS.NOTIFY_GENERATION_FAILED",
        ),
      );
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
          title: "Nouvelle version",
          message: "Créer une nouvelle version de la grille active ?",
          confirmLabel: "Créer",
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
  gridBlocks(): TimelineBlock[] {
    return (this.channel?.grid_data?.blocks ?? []).map((b) => ({
      start: b.starts_at.slice(0, 5),
      end: b.ends_at.slice(0, 5),
      title: `Bloc — ${b.allowed_categories[0] ?? "Programmation"}`,
      sub: `Priorité ${b.priority}`,
      category: natureToCategory(b.allowed_natures[0]),
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
        category: natureToCategory(i.role),
      }));
  }
  blockTags(b: GridBlock) {
    return [
      ...b.allowed_categories,
      ...b.allowed_natures,
      ...b.allowed_container_kinds,
    ].slice(0, 4);
  }
  shift(d: number) {
    const next = new Date(this.calendarDate);
    next.setDate(next.getDate() + d);
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
