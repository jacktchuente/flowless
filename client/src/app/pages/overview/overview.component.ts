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
import { TranslateModule, TranslateService } from "@ngx-translate/core";
@Component({
  standalone: true,
  imports: [
    DatePipe,
    NgFor,
    NgIf,
    RouterLink,
    TimeAgoPipe,
    FlwIconComponent,
    TranslateModule,
  ],
  templateUrl: "./overview.component.html",
  styleUrl: "./overview.component.css",
})
export class OverviewComponent {
  private destroyRef = inject(DestroyRef);
  data: DashboardOverview | null = null;
  constructor(
    private service: DashboardService,
    private translate: TranslateService,
  ) {
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
    return this.translate.instant(
      `OVERVIEW.ACTIVITY.${a.kind.toUpperCase()}`,
      a.label_params,
    );
  }
  alertMessage(alert: {
    kind: string;
    message: string | null;
    message_params?: Record<string, unknown>;
  }) {
    return (
      alert.message ||
      this.translate.instant(
        `OVERVIEW.ALERTS.${alert.kind.toUpperCase()}`,
        alert.message_params,
      )
    );
  }
}
