import { Component, DestroyRef, inject } from "@angular/core";
import { NgFor, NgIf } from "@angular/common";
import { takeUntilDestroyed } from "@angular/core/rxjs-interop";
import { TranslateModule, TranslateService } from "@ngx-translate/core";
import { MediaSource } from "@project-interfaces/media-source";
import { MediaSourceService } from "@project-services/media-source.service";
import { NotificationService } from "@project-shared/services/notification.service";
import { FlwDialogService } from "../../../ui/dialog.service";
import { FlwIconComponent } from "../../../ui/icon/flw-icon.component";
import { TimeAgoPipe } from "../../../ui/pipes/time-ago.pipe";
import { FlwConfirmComponent } from "../../../ui/confirm/flw-confirm.component";
import { FlwSwitchComponent } from "../../../ui/switch/flw-switch.component";
import { MediaSourceDialogComponent } from "../media-source-dialog/media-source-dialog.component";
@Component({
  selector: "app-media-source",
  standalone: true,
  imports: [NgFor, NgIf, TranslateModule, FlwIconComponent, FlwSwitchComponent, TimeAgoPipe],
  templateUrl: "./media-source.component.html",
  styleUrl: "./media-source.component.css",
})
export class MediaSourceComponent {
  private destroyRef = inject(DestroyRef);
  sources: MediaSource[] = [];
  readonly syncingIds = new Set<string>();
  constructor(
    private service: MediaSourceService,
    private notification: NotificationService,
    private dialogs: FlwDialogService,
    private translate: TranslateService,
  ) {
    service.listObject(null, true);
    service
      .getObjectBehaviorSubject()
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe((v) => (this.sources = v));
  }
  get staleSources() {
    return this.sources.filter((s) => this.isStale(s));
  }
  daysSince(source: MediaSource) {
    return source.analyzed_at
      ? Math.floor(
          (Date.now() - new Date(source.analyzed_at).getTime()) / 86400000,
        )
      : Infinity;
  }
  isStale(source: MediaSource) {
    return !source.analyzed_at || this.daysSince(source) > 7;
  }
  status(source: MediaSource) {
    if (source.analyze_status === 1)
      return { kind: "info", label: "MEDIA_SOURCE.STATUS_SYNCING" };
    if (this.isStale(source))
      return { kind: "warning", label: "MEDIA_SOURCE.STATUS_STALE" };
    return { kind: "success", label: "MEDIA_SOURCE.STATUS_CONNECTED" };
  }
  openCreateDialog() {
    this.dialogs.open(MediaSourceDialogComponent, { data: {} });
  }
  openEditDialog(source: MediaSource, e?: Event) {
    e?.stopPropagation();
    this.dialogs.open(MediaSourceDialogComponent, { data: { source } });
  }
  deleteSource(source: MediaSource, e?: Event) {
    e?.stopPropagation();
    this.dialogs
      .open(FlwConfirmComponent, {
        data: {
          title: this.translate.instant("MEDIA_SOURCE.DELETE_TITLE"),
          message: this.translate.instant("MEDIA_SOURCE.CONFIRM_DELETE", {
            name: source.name,
          }),
          confirmLabel: this.translate.instant("COMMON.DELETE"),
        },
      })
      .closed.subscribe((ok) => {
        if (ok)
          this.service.deleteObject(String(source.id)).subscribe((r) => {
            if (!r.isOk)
              this.notification.notify("MEDIA_SOURCE.NOTIFY_DELETE_FAILED");
          });
      });
  }
  toggleActive(source: MediaSource, isActive: boolean) {
    this.service.setActive(source.id, isActive).subscribe((r) => {
      if (!r.isOk) {
        source.is_active = !isActive;
        this.notification.notify("MEDIA_SOURCE.NOTIFY_ACTIVE_FAILED");
        return;
      }
      source.is_active = isActive;
    });
  }
  syncCollections(source: MediaSource, e?: Event) {
    e?.stopPropagation();
    const id = String(source.id);
    if (this.syncingIds.has(id)) return;
    this.syncingIds.add(id);
    this.service.syncCollections(source.id).subscribe((r) => {
      this.syncingIds.delete(id);
      if (!r.isOk) {
        this.notification.notify("MEDIA_SOURCE.NOTIFY_SYNC_FAILED");
        return;
      }
      source.analyze_status = 1;
      this.notification.notify("MEDIA_SOURCE.NOTIFY_SYNC_STARTED");
    });
  }
}
