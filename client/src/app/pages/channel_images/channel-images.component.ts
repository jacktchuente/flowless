import { Component, DestroyRef, inject } from "@angular/core";
import { NgClass, NgFor, NgIf } from "@angular/common";
import { FormsModule } from "@angular/forms";
import { ActivatedRoute } from "@angular/router";
import { takeUntilDestroyed } from "@angular/core/rxjs-interop";
import { filter } from "rxjs";
import { WebsocketService } from "@kwyxyz/ngx-request";
import {
  ChannelImageEntityType,
  ChannelImageQueryPreview,
  ChannelImageSuggestion,
  ChannelImageSuggestionRun,
} from "@project-interfaces/channel-image";
import { TvChannel } from "@project-interfaces/tv-channel";
import { ChannelImageService } from "@project-services/channel-image.service";
import { TvChannelService } from "@project-services/tv-channel.service";
import { NotificationService } from "@project-shared/services/notification.service";
import { AnalyzeStatus } from "../../_utils/analyze-status";
import { FlwConfirmComponent } from "../../ui/confirm/flw-confirm.component";
import { FlwDialogService } from "../../ui/dialog.service";
import { FlwIconComponent } from "../../ui/icon/flw-icon.component";
import { FlwSelectComponent } from "../../ui/select/flw-select.component";
import { TimeAgoPipe } from "../../ui/pipes/time-ago.pipe";
import { TranslateModule, TranslateService } from "@ngx-translate/core";

@Component({
  standalone: true,
  imports: [
    NgClass,
    NgFor,
    NgIf,
    FormsModule,
    FlwIconComponent,
    FlwSelectComponent,
    TimeAgoPipe,
    TranslateModule,
  ],
  templateUrl: "./channel-images.component.html",
  styleUrl: "./channel-images.component.css",
})
export class ChannelImagesComponent {
  private destroyRef = inject(DestroyRef);
  channels: TvChannel[] = [];
  selectedChannelId: string | null = null;
  runs: ChannelImageSuggestionRun[] = [];
  query = "";
  entityType: ChannelImageEntityType = "theme";
  querySourceHint: string | null = null;
  isSearching = false;
  isChoosing = false;
  entityOptions: Array<{ label: string; value: ChannelImageEntityType }> = [];

  constructor(
    private channelsService: TvChannelService,
    private imageService: ChannelImageService,
    private notification: NotificationService,
    private dialogs: FlwDialogService,
    private translate: TranslateService,
    route: ActivatedRoute,
    websocket: WebsocketService,
  ) {
    this.entityOptions = (["studio", "person", "theme"] as const).map((value) => ({
      label: this.translate.instant(`CHANNEL_IMAGES.ENTITY.${value.toUpperCase()}`),
      value,
    }));
    // Deep-link depuis le detail chaine: /app/channel-images?channel={id}
    const requestedChannelId = route.snapshot.queryParamMap.get("channel");
    this.channelsService
      .getObjectBehaviorSubject()
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe((channels) => {
        this.channels = channels;
        if (this.selectedChannelId) return;
        const requested = requestedChannelId
          ? channels.find(
              (channel: TvChannel) => String(channel.id) === requestedChannelId,
            )
          : null;
        if (requested) {
          this.select(requested);
        } else if (channels.length) {
          this.select(channels[0]);
        }
      });
    this.channelsService.listObject(null, true);
    websocket.crudEvent
      .pipe(
        filter((event: any) => {
          const type = event.type?.toLowerCase?.() ?? "";
          return type === "channelimagesuggestionrun" || type === "tvchannel";
        }),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe(() => {
        if (this.selectedChannelId) this.loadRuns(this.selectedChannelId);
      });
  }

  isSelected(channel: TvChannel): boolean {
    return String(channel.id) === this.selectedChannelId;
  }

  get selectedChannel(): TvChannel | null {
    return (
      this.channels.find(
        (channel) => String(channel.id) === this.selectedChannelId,
      ) ?? null
    );
  }

  get latestRun(): ChannelImageSuggestionRun | null {
    return this.runs[0] ?? null;
  }

  get previousRuns(): ChannelImageSuggestionRun[] {
    return this.runs.slice(1);
  }

  get isRunning(): boolean {
    return this.isSearching || this.latestRun?.status === AnalyzeStatus.Running;
  }

  runWarnings(run: ChannelImageSuggestionRun): string[] {
    return run.diagnostics?.warnings ?? [];
  }

  select(channel: TvChannel) {
    this.selectedChannelId = String(channel.id);
    this.runs = [];
    this.query = "";
    this.querySourceHint = null;
    this.loadRuns(channel.id);
    this.channelsService
      .getImageQueryPreview(channel.id)
      .subscribe((response) => {
        if (String(channel.id) !== this.selectedChannelId) return;
        const preview = response.body as ChannelImageQueryPreview | null;
        if (response.isOk && preview?.query && !this.query) {
          this.query = preview.query;
          this.entityType = preview.entity_type ?? "theme";
          this.querySourceHint = preview.source;
        }
      });
  }

  loadRuns(channelId: string | number) {
    this.imageService.listRuns(channelId).subscribe((response) => {
      if (String(channelId) !== this.selectedChannelId) return;
      if (!response.isOk) return;
      this.runs = response.body as ChannelImageSuggestionRun[];
      this.isSearching = false;
      const latest = this.latestRun;
      if (latest?.query && !this.query) {
        this.query = latest.query;
        this.entityType = (latest.entity_type || "theme") as ChannelImageEntityType;
      }
    });
  }

  search() {
    if (!this.selectedChannelId || this.isRunning) return;
    this.isSearching = true;
    this.imageService
      .createRun({
        tv_channel: this.selectedChannelId,
        query: this.query.trim(),
        entity_type: this.query.trim() ? this.entityType : undefined,
      })
      .subscribe((response) => {
        if (!response.isOk) {
          this.isSearching = false;
          this.notification.notify("CHANNEL_IMAGES.NOTIFY_SEARCH_FAILED");
        }
      });
  }

  choose(run: ChannelImageSuggestionRun, suggestion: ChannelImageSuggestion) {
    if (this.isChoosing) return;
    this.dialogs
      .open(FlwConfirmComponent, {
        data: {
          title: this.translate.instant("CHANNEL_IMAGES.CONFIRM_TITLE"),
          message: this.translate.instant("CHANNEL_IMAGES.CONFIRM_MESSAGE", {
            channel: this.selectedChannel?.name ?? "",
          }),
          confirmLabel: this.translate.instant("CHANNEL_IMAGES.CONFIRM_APPLY"),
        },
      })
      .closed.subscribe((confirmed) => {
        if (!confirmed) return;
        this.isChoosing = true;
        this.imageService.choose(run.id, suggestion.id).subscribe((response) => {
          this.isChoosing = false;
          if (!response.isOk) {
            this.notification.notify("CHANNEL_IMAGES.NOTIFY_APPLY_FAILED");
            return;
          }
          this.notification.notify("CHANNEL_IMAGES.NOTIFY_APPLIED");
          this.channelsService.listObject(null, true);
          if (this.selectedChannelId) this.loadRuns(this.selectedChannelId);
        });
      });
  }

  deleteRun(run: ChannelImageSuggestionRun) {
    this.imageService.deleteRun(run.id).subscribe((response) => {
      if (response.isOk && this.selectedChannelId) {
        this.loadRuns(this.selectedChannelId);
      }
    });
  }

  statusPill(run: ChannelImageSuggestionRun): { kind: string; label: string } {
    if (run.status === AnalyzeStatus.Running)
      return { kind: "info", label: this.translate.instant("CHANNEL_IMAGES.STATUS_RUNNING") };
    if (run.status === AnalyzeStatus.DoneWithErrors)
      return { kind: "warning", label: this.translate.instant("CHANNEL_IMAGES.STATUS_WARNINGS") };
    return { kind: "success", label: this.translate.instant("CHANNEL_IMAGES.STATUS_DONE") };
  }
}
