import { Component, DestroyRef, HostListener, inject } from "@angular/core";
import { DatePipe, NgFor, NgIf } from "@angular/common";
import { RouterLink } from "@angular/router";
import { interval, startWith, switchMap } from "rxjs";
import { takeUntilDestroyed } from "@angular/core/rxjs-interop";
import {
  DashboardOverview,
  DashboardActivity,
} from "../../_interfaces/dashboard";
import { DashboardService } from "../../_services/dashboard.service";
import { TimeAgoPipe } from "../../ui/pipes/time-ago.pipe";
import { FlwIconComponent } from "../../ui/icon/flw-icon.component";
@Component({
  standalone: true,
  imports: [DatePipe, NgFor, NgIf, RouterLink, TimeAgoPipe, FlwIconComponent],
  templateUrl: "./overview.component.html",
  styleUrl: "./overview.component.css",
})
export class OverviewComponent {
  private destroyRef = inject(DestroyRef);
  data: DashboardOverview | null = null;
  constructor(private service: DashboardService) {
    interval(60000)
      .pipe(
        startWith(0),
        switchMap(() => service.overview()),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe((v) => (this.data = v));
  }
  @HostListener("window:focus") focus() {
    this.service.overview().subscribe((v) => (this.data = v));
  }
  minutes(value: string | null) {
    return value
      ? Math.max(
          0,
          Math.floor((Date.now() - new Date(value).getTime()) / 60000),
        )
      : "—";
  }
  activity(a: DashboardActivity) {
    const p = a.label_params as any;
    if (a.kind === "playout_generated")
      return `Planning de ${p.channel} généré pour ${p.days} jour(s)`;
    if (a.kind === "playout_failed")
      return `Échec de génération pour ${p.channel}`;
    if (a.kind === "collection_analyzed")
      return `Collection ${p.collection} analysée`;
    return `Analyse éditoriale de ${p.catalog}`;
  }
}
