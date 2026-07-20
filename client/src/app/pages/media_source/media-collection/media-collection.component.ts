import { Component, DestroyRef, inject } from "@angular/core";
import { DatePipe, NgFor, NgIf } from "@angular/common";
import { takeUntilDestroyed } from "@angular/core/rxjs-interop";
import { TranslateModule, TranslateService } from "@ngx-translate/core";
import { MediaCollection } from "@project-interfaces/media-collection";
import { MediaCollectionService } from "@project-services/media-collection.service";
import { NotificationService } from "@project-shared/services/notification.service";
import { AnalyzeStatus } from "../../../_utils/analyze-status";
import { FlwDialogService } from "../../../ui/dialog.service";
import { FlwSwitchComponent } from "../../../ui/switch/flw-switch.component";
import { FlwIconComponent } from "../../../ui/icon/flw-icon.component";
import { FlwConfirmComponent } from "../../../ui/confirm/flw-confirm.component";
import { MediaCollectionDetailDialogComponent } from "../media-collection-detail-dialog/media-collection-detail-dialog.component";
@Component({
  selector: "app-media-collection",
  standalone: true,
  imports: [
    DatePipe,
    NgFor,
    NgIf,
    TranslateModule,
    FlwSwitchComponent,
    FlwIconComponent,
  ],
  templateUrl: "./media-collection.component.html",
  styleUrl: "./media-collection.component.css",
})
export class MediaCollectionComponent {
  private destroyRef = inject(DestroyRef);
  collections: MediaCollection[] = [];
  syncingIds = new Set<string>();
  constructor(
    private service: MediaCollectionService,
    private dialogs: FlwDialogService,
    private notification: NotificationService,
    private translate: TranslateService,
  ) {
    service.listObject(null, true);
    service
      .getObjectBehaviorSubject()
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe((v) => (this.collections = v));
  }
  openDetail(collection: MediaCollection) {
    this.dialogs.open(MediaCollectionDetailDialogComponent, {
      data: { collection },
    });
  }
  toggleActive(collection: MediaCollection, value: boolean) {
    collection.is_active = value;
    this.service
      .patchObject(String(collection.id), { is_active: value })
      .subscribe((r) => {
        if (!r.isOk) {
          collection.is_active = !value;
          this.notification.notify("MEDIA_COLLECTION.NOTIFY_TOGGLE_FAILED");
        }
      });
  }
  // L'analyse (etiquetage LLM) est reservee aux collections au role principal.
  isMainRole(collection: MediaCollection) {
    return collection.programming_role === 1;
  }
  analyze(collection: MediaCollection, e?: Event) {
    e?.stopPropagation();
    if (!collection.is_active || !this.isMainRole(collection)) return;
    const alreadyAnalyzed = !!collection.analyzed_at;
    const isAnalyzing = collection.analyze_status === AnalyzeStatus.Running;
    this.dialogs
      .open(FlwConfirmComponent, {
        data: {
          title: this.translate.instant("MEDIA_COLLECTION.ANALYZE_COLLECTION"),
          message: this.translate.instant("MEDIA_COLLECTION.CONFIRM_ANALYZE", {
            name: collection.name,
          }),
          warning: isAnalyzing
            ? this.translate.instant("MEDIA_COLLECTION.ANALYZING_WARNING")
            : undefined,
          confirmLabel: this.translate.instant("MEDIA_COLLECTION.ANALYZE"),
          extraLabel:
            alreadyAnalyzed || isAnalyzing
              ? this.translate.instant("MEDIA_COLLECTION.FORCE_REANALYZE")
              : undefined,
        },
      })
      .closed.subscribe((result) => {
        if (!result) return;
        const id = String(collection.id);
        this.syncingIds.add(id);
        this.service
          .analyze(collection.id, result === "extra")
          .subscribe((r) => {
            this.syncingIds.delete(id);
            if (!r.isOk) {
              this.notification.notify(
                "MEDIA_COLLECTION.NOTIFY_ANALYZE_FAILED",
              );
              return;
            }
            collection.analyze_status = 1;
            this.notification.notify("MEDIA_COLLECTION.NOTIFY_ANALYZE_STARTED");
          });
      });
  }
  role(c: MediaCollection) {
    return this.label(c.programming_role, ROLES);
  }
  nature(c: MediaCollection) {
    return this.label(c.nature, NATURES);
  }
  kind(c: MediaCollection) {
    return this.label(c.container_kind, KINDS);
  }
  rolePill(c: MediaCollection) {
    return c.programming_role === 1
      ? "info"
      : c.programming_role === 7
        ? "neutral"
        : "warning";
  }
  private label(
    value: number | null,
    options: { value: number; label: string }[],
  ) {
    const key = options.find((o) => o.value === value)?.label;
    return key ? this.translate.instant(key) : "—";
  }
}
export const ROLES = [1, 2, 3, 4, 5, 6, 7, 8, 99].map((value) => ({
  value,
  label: `UI.ROLES.${value}`,
}));
export const NATURES = [1, 2, 3, 4, 5, 6, 99].map((value) => ({
  value,
  label: `UI.NATURES.${value}`,
}));
export const KINDS = [1, 2, 3, 4, 99].map((value) => ({
  value,
  label: `UI.CONTAINER_KINDS.${value}`,
}));
