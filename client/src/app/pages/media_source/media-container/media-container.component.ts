import { Component, DestroyRef, Inject, inject } from "@angular/core";
import { DatePipe, NgFor, NgIf } from "@angular/common";
import { FormControl, FormsModule, ReactiveFormsModule } from "@angular/forms";
import { DIALOG_DATA, DialogRef } from "@angular/cdk/dialog";
import { debounceTime, filter } from "rxjs";
import { takeUntilDestroyed } from "@angular/core/rxjs-interop";
import { TranslateModule, TranslateService } from "@ngx-translate/core";
import { WebsocketService } from "@kwyxyz/ngx-request";
import {
  MediaContainerListItem,
  PaginatedResponse,
} from "@project-interfaces/media-container";
import { MediaContainerService } from "@project-services/media-container.service";
import { NotificationService } from "@project-shared/services/notification.service";
import { FlwDialogService } from "../../../ui/dialog.service";
import { FlwIconComponent } from "../../../ui/icon/flw-icon.component";
import { FlwChipFilterComponent } from "../../../ui/chip-filter/flw-chip-filter.component";
import { FlwSelectComponent } from "../../../ui/select/flw-select.component";
import { FlwPaginationComponent } from "../../../ui/pagination/flw-pagination.component";
import { FlwConfirmComponent } from "../../../ui/confirm/flw-confirm.component";
import { FlwModalComponent } from "../../../ui/modal/flw-modal.component";
import { MediaContainerDetailDialogComponent } from "../media-container-dialog/media-container-dialog.component";
const STATUS = [
  { value: "", label: "MEDIA_CONTAINER.FILTERS.ANY_M" },
  { value: "2", label: "MEDIA_CONTAINER.STATUS_COMPLETE" },
  { value: "4", label: "MEDIA_CONTAINER.STATUS_ERROR" },
  { value: "1", label: "MEDIA_CONTAINER.STATUS_PENDING" },
  { value: "0", label: "MEDIA_CONTAINER.STATUS_PARTIAL" },
];
const NATURE = [
  { value: "", label: "MEDIA_CONTAINER.FILTERS.ANY_F" },
  ...["1", "2", "3", "4", "5", "6", "99"].map((value) => ({
    value,
    label: `UI.NATURES.${value}`,
  })),
];
const KIND = [
  { value: "", label: "MEDIA_CONTAINER.FILTERS.ANY_M" },
  ...["1", "2", "3", "4", "99"].map((value) => ({
    value,
    label: `UI.CONTAINER_KINDS.${value}`,
  })),
];
@Component({
  standalone: true,
  imports: [
    FormsModule,
    TranslateModule,
    FlwModalComponent,
    FlwSelectComponent,
  ],
  template: `<flw-modal
    [title]="'MEDIA_CONTAINER.FILTERS.TITLE' | translate"
    [description]="'MEDIA_CONTAINER.FILTERS.DESCRIPTION' | translate"
    ><div class="field-row cols-2">
      <div class="field">
        <label>{{ "MEDIA_CONTAINER.FILTERS.STATUS" | translate }}</label
        ><flw-select [(ngModel)]="draft.status" [options]="status" />
      </div>
      <div class="field">
        <label>{{ "MEDIA_CONTAINER.FILTERS.CATEGORY" | translate }}</label
        ><input [(ngModel)]="draft.category" type="text" />
      </div>
      <div class="field">
        <label>{{ "MEDIA_CONTAINER.FILTERS.NATURE" | translate }}</label
        ><flw-select [(ngModel)]="draft.nature" [options]="natures" />
      </div>
      <div class="field">
        <label>{{ "MEDIA_CONTAINER.FILTERS.TYPE" | translate }}</label
        ><flw-select [(ngModel)]="draft.container_kind" [options]="kinds" />
      </div>
      <div class="field">
        <label>{{ "MEDIA_CONTAINER.FILTERS.ANIME" | translate }}</label
        ><flw-select [(ngModel)]="draft.is_anime" [options]="anime" />
      </div>
    </div>
    <div modal-footer>
      <button class="btn ghost" type="button" (click)="reset()">
        {{ "COMMON.RESET" | translate }}
      </button>
      <div>
        <button class="btn ghost" type="button" (click)="ref.close()">
          {{ "COMMON.CANCEL" | translate }}</button
        ><button class="btn primary" type="button" (click)="ref.close(draft)">
          {{ "COMMON.APPLY" | translate }}
        </button>
      </div>
    </div></flw-modal
  >`,
})
export class MediaFiltersDialog {
  draft = { ...this.data };
  status = this.translated(STATUS);
  natures = this.translated(NATURE);
  kinds = this.translated(KIND);
  anime = this.translated([
    { value: "", label: "MEDIA_CONTAINER.FILTERS.ANY_M" },
    { value: "1", label: "MEDIA_CONTAINER.FILTERS.ANIME_ONLY" },
    { value: "0", label: "MEDIA_CONTAINER.FILTERS.NOT_ANIME" },
  ]);
  constructor(
    private translate: TranslateService,
    @Inject(DIALOG_DATA) public data: any,
    public ref: DialogRef<any>,
  ) {}
  private translated(options: { value: string; label: string }[]) {
    return options.map((o) => ({
      ...o,
      label: this.translate.instant(o.label),
    }));
  }
  reset() {
    this.draft = {
      status: "",
      category: "",
      nature: "",
      container_kind: "",
      is_anime: "",
    };
  }
}
@Component({
  selector: "app-media-container",
  standalone: true,
  imports: [
    DatePipe,
    NgFor,
    NgIf,
    ReactiveFormsModule,
    TranslateModule,
    FlwIconComponent,
    FlwChipFilterComponent,
    FlwSelectComponent,
    FlwPaginationComponent,
  ],
  templateUrl: "./media-container.component.html",
  styleUrl: "./media-container.component.css",
})
export class MediaContainerComponent {
  private destroyRef = inject(DestroyRef);
  search = new FormControl("", { nonNullable: true });
  containers: MediaContainerListItem[] = [];
  filters = {
    status: "",
    category: "",
    nature: "",
    container_kind: "",
    is_anime: "",
  };
  currentPage = 1;
  pageSize = 10;
  totalCount = 0;
  isLoading = false;
  syncingIds = new Set<string>();
  pageSizeOptions = [
    { value: 10, label: "10 / page" },
    { value: 25, label: "25 / page" },
    { value: 50, label: "50 / page" },
  ];
  constructor(
    private service: MediaContainerService,
    private notification: NotificationService,
    private dialogs: FlwDialogService,
    ws: WebsocketService,
    private translate: TranslateService,
  ) {
    this.loadPage(1);
    this.search.valueChanges
      .pipe(debounceTime(300), takeUntilDestroyed(this.destroyRef))
      .subscribe(() => this.loadPage(1));
    ws.crudEvent
      .pipe(
        filter((e: any) => e.type?.toLowerCase?.() === "mediacontainer"),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe(() => this.loadPage(this.currentPage));
  }
  get totalPages() {
    return Math.max(1, Math.ceil(this.totalCount / this.pageSize));
  }
  get chips() {
    const labels: any = {
      status: "MEDIA_CONTAINER.FILTERS.STATUS",
      category: "MEDIA_CONTAINER.FILTERS.CATEGORY",
      nature: "MEDIA_CONTAINER.FILTERS.NATURE",
      container_kind: "MEDIA_CONTAINER.FILTERS.TYPE",
      is_anime: "MEDIA_CONTAINER.FILTERS.ANIME",
    };
    return Object.entries(this.filters)
      .filter(([, v]) => v !== "")
      .map(([key, value]) => ({
        key,
        label: `${this.translate.instant(labels[key])} : ${this.optionLabel(key, value)}`,
      }));
  }
  loadPage(page: number) {
    if (page < 1) return;
    this.isLoading = true;
    this.service.listPage(this.params(page)).subscribe((r) => {
      this.isLoading = false;
      if (!r.isOk) {
        this.notification.notify("MEDIA_CONTAINER.NOTIFY_LOAD_FAILED");
        return;
      }
      const p = r.body as PaginatedResponse<MediaContainerListItem>;
      this.currentPage = page;
      this.totalCount = p.count;
      this.containers = p.results;
    });
  }
  openFilters() {
    this.dialogs
      .open(MediaFiltersDialog, { data: { ...this.filters } })
      .closed.subscribe((v) => {
        if (v) {
          this.filters = v;
          this.loadPage(1);
        }
      });
  }
  removeFilter(key: string) {
    (this.filters as any)[key] = "";
    this.loadPage(1);
  }
  resetFilters() {
    this.filters = {
      status: "",
      category: "",
      nature: "",
      container_kind: "",
      is_anime: "",
    };
    this.loadPage(1);
  }
  pageSizeChange(v: unknown) {
    this.pageSize = Number(v);
    this.loadPage(1);
  }
  openDetail(c: MediaContainerListItem) {
    this.dialogs.open(MediaContainerDetailDialogComponent, {
      data: { containerId: c.id },
    });
  }
  analyze(c: MediaContainerListItem, e?: Event) {
    e?.stopPropagation();
    const id = String(c.id);
    if (this.syncingIds.has(id)) return;
    this.syncingIds.add(id);
    this.service.analyze(c.id).subscribe((r) => {
      this.syncingIds.delete(id);
      if (!r.isOk) {
        this.notification.notify("MEDIA_CONTAINER.NOTIFY_ANALYZE_FAILED");
        return;
      }
      c.analyze_status = 1;
      this.notification.notify("MEDIA_CONTAINER.NOTIFY_ANALYZE_STARTED");
    });
  }
  analyzeAll() {
    this.dialogs
      .open(FlwConfirmComponent, {
        data: {
          title: this.translate.instant("MEDIA_CONTAINER.ANALYZE_ALL_TITLE"),
          message: this.translate.instant(
            "MEDIA_CONTAINER.CONFIRM_ANALYZE_ALL",
          ),
          confirmLabel: this.translate.instant("MEDIA_CONTAINER.ANALYZE_ALL"),
        },
      })
      .closed.subscribe((ok) => {
        if (ok)
          this.service.analyzeAll().subscribe((r) => {
            if (r.isOk) {
              this.containers.forEach((c) => (c.analyze_status = 1));
              this.notification.notify(
                "MEDIA_CONTAINER.NOTIFY_ANALYZE_ALL_STARTED",
              );
            } else
              this.notification.notify(
                "MEDIA_CONTAINER.NOTIFY_ANALYZE_ALL_FAILED",
              );
          });
      });
  }
  status(c: MediaContainerListItem) {
    if (c.analyze_status === 2)
      return { kind: "success", label: "MEDIA_CONTAINER.STATUS_COMPLETE" };
    if (c.analyze_status === 4)
      return { kind: "critical", label: "MEDIA_CONTAINER.STATUS_ERROR" };
    if (c.analyze_status === 1)
      return { kind: "info", label: "MEDIA_CONTAINER.STATUS_ANALYZING" };
    return { kind: "warning", label: "MEDIA_CONTAINER.STATUS_PARTIAL" };
  }
  nature(c: MediaContainerListItem) {
    return this.findLabel(NATURE, String(c.nature ?? ""));
  }
  kind(c: MediaContainerListItem) {
    return this.findLabel(KIND, String(c.container_kind ?? ""));
  }
  private findLabel(
    options: { value: string; label: string }[],
    value: string,
  ) {
    const key = value === "" ? null : options.find((o) => o.value === value);
    return key ? this.translate.instant(key.label) : "—";
  }
  private optionLabel(key: string, v: string) {
    if (key === "status") {
      const option = STATUS.find((o) => o.value === v);
      return option ? this.translate.instant(option.label) : v;
    }
    if (key === "nature") return this.findLabel(NATURE, v);
    if (key === "container_kind") return this.findLabel(KIND, v);
    if (key === "is_anime")
      return this.translate.instant(v === "1" ? "COMMON.YES" : "COMMON.NO");
    return v;
  }
  private params(page: number) {
    const p: any = { page, page_size: this.pageSize };
    if (this.search.value.trim()) p.title = this.search.value.trim();
    Object.entries(this.filters).forEach(([k, v]) => {
      if (v !== "") p[k] = v;
    });
    return p;
  }
}
