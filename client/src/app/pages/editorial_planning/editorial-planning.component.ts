import { Component, DestroyRef, inject } from "@angular/core";
import { DecimalPipe, NgFor, NgIf } from "@angular/common";
import { FormsModule } from "@angular/forms";
import { ActivatedRoute, Router } from "@angular/router";
import { takeUntilDestroyed } from "@angular/core/rxjs-interop";
import { Catalog } from "../../_interfaces/catalog";
import { MediaCollection } from "../../_interfaces/media-collection";
import {
  EditorialChannelCandidate,
  EditorialFlowRun,
  EditorialSegment,
  EditorialSegmentMembership,
} from "../../_interfaces/editorial-planning";
import { CatalogService } from "../../_services/catalog.service";
import { MediaCollectionService } from "../../_services/media-collection.service";
import { EditorialPlanningService } from "../../_services/editorial-planning.service";
import { NotificationService } from "../../_shared/services/notification.service";
import { FlwSelectComponent } from "../../ui/select/flw-select.component";
import { FlwTabsComponent } from "../../ui/tabs/flw-tabs.component";
import { FlwSwitchComponent } from "../../ui/switch/flw-switch.component";
import { FlwGenStepsComponent } from "../../ui/gen-steps/flw-gen-steps.component";
import { TimeAgoPipe } from "../../ui/pipes/time-ago.pipe";
@Component({
  standalone: true,
  imports: [
    DecimalPipe,
    NgFor,
    NgIf,
    FormsModule,
    FlwSelectComponent,
    FlwTabsComponent,
    FlwSwitchComponent,
    FlwGenStepsComponent,
    TimeAgoPipe,
  ],
  templateUrl: "./editorial-planning.component.html",
  styleUrl: "./editorial-planning.component.css",
})
export class EditorialPlanningComponent {
  private destroyRef = inject(DestroyRef);
  catalogs: Catalog[] = [];
  collections: MediaCollection[] = [];
  selected = new Set<string>();
  catalogId: string | null = null;
  active = "collections";
  tabs = [
    { id: "collections", label: "1 · Collections" },
    { id: "analysis", label: "2 · Lancer l’analyse" },
    { id: "segments", label: "3 · Segments" },
    { id: "candidates", label: "4 · Candidats" },
    { id: "review", label: "5 · Revue" },
  ];
  target = 4;
  maxCandidates = 8;
  multi = true;
  sharing = false;
  threshold = 70;
  generation: "idle" | "running" | "done" | "error" = "idle";
  runs: EditorialFlowRun[] = [];
  segments: EditorialSegment[] = [];
  candidates: EditorialChannelCandidate[] = [];
  memberships: EditorialSegmentMembership[] = [];
  selectedSegment: EditorialSegment | null = null;
  search = "";
  constructor(
    private catalogService: CatalogService,
    collectionsService: MediaCollectionService,
    private planning: EditorialPlanningService,
    private notification: NotificationService,
    route: ActivatedRoute,
    private router: Router,
  ) {
    const requested = route.snapshot.queryParamMap.get("catalog");
    catalogService
      .getObjectBehaviorSubject()
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe((v) => {
        this.catalogs = v;
        if (!this.catalogId && v.length) {
          this.catalogId =
            requested && v.some((c: Catalog) => String(c.id) === requested)
              ? requested
              : String(v[0].id);
          this.load();
        }
      });
    collectionsService.listObject(null, true);
    collectionsService
      .getObjectBehaviorSubject()
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe(
        (v) =>
          (this.collections = v.filter(
            (c: MediaCollection) => c.is_active && c.analyze_status === 2,
          )),
      );
  }
  get catalogOptions() {
    return this.catalogs.map((c) => ({ label: c.name, value: String(c.id) }));
  }
  get visibleCollections() {
    return this.collections.filter((c) =>
      c.name.toLowerCase().includes(this.search.toLowerCase()),
    );
  }
  toggle(id: string | number, on: boolean) {
    on ? this.selected.add(String(id)) : this.selected.delete(String(id));
  }
  changeCatalog(v: unknown) {
    this.catalogId = String(v);
    this.router.navigate([], {
      queryParams: { catalog: this.catalogId },
      queryParamsHandling: "merge",
    });
    this.load();
  }
  load() {
    if (!this.catalogId) return;
    this.planning.listRuns(this.catalogId).subscribe((r) => {
      if (r.isOk) this.runs = r.body as EditorialFlowRun[];
    });
    this.planning.listSegmentsForCatalog(this.catalogId).subscribe((r) => {
      if (r.isOk) {
        this.segments = r.body as EditorialSegment[];
        if (this.segments.length && !this.selectedSegment)
          this.selectSegment(this.segments[0]);
      }
    });
    this.planning.listCandidates({ catalog: this.catalogId }).subscribe((r) => {
      if (r.isOk) this.candidates = r.body as EditorialChannelCandidate[];
    });
  }
  generate() {
    if (!this.catalogId || !this.selected.size) return;
    this.generation = "running";
    this.catalogService
      .generateEditorialPlanning(this.catalogId, {
        media_collection_ids: [...this.selected],
        target_channel_count: this.target,
        max_channel_candidates: this.maxCandidates,
        allow_multi_segment: this.multi,
        allow_segment_sharing: this.sharing,
        refine_membership_threshold: this.threshold / 100,
      })
      .subscribe((r) => {
        if (!r.isOk) {
          this.generation = "error";
          return;
        }
        this.notification.notify("CHANNELS.NOTIFY_GENERATION_STARTED");
        setTimeout(() => {
          this.generation = "done";
          this.load();
        }, 2500);
      });
  }
  selectSegment(segment: EditorialSegment) {
    this.selectedSegment = segment;
    this.planning.listMemberships(segment.id).subscribe((r) => {
      if (r.isOk) this.memberships = r.body as EditorialSegmentMembership[];
    });
  }
  setStatus(m: EditorialSegmentMembership, status: string) {
    this.planning.setMembershipStatus(m.id, status).subscribe((r) => {
      if (r.isOk) m.status = (r.body as EditorialSegmentMembership).status;
    });
  }
  promote(c: EditorialChannelCandidate) {
    this.planning.createFlexibleChannel(c.id, c.name).subscribe((r) => {
      if (r.isOk) {
        this.notification.notify("Chaîne flexible créée.");
        this.load();
      }
    });
  }
  activate(run: EditorialFlowRun) {
    this.planning.activateRun(run.id).subscribe(() => this.load());
  }
  match() {
    if (this.catalogId)
      this.planning
        .matchNewMediaForCatalog(this.catalogId)
        .subscribe((r) =>
          this.notification.notify(
            r.isOk ? "Nouveaux médias intégrés." : "Aucun run actif.",
          ),
        );
  }
  percent(v: number) {
    return Math.round(v * 100);
  }
}
