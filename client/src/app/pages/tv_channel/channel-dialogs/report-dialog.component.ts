import { Component, Inject } from "@angular/core";
import { DatePipe, NgFor, NgIf } from "@angular/common";
import { DIALOG_DATA, DialogRef } from "@angular/cdk/dialog";
import { PlayoutGenerationReport } from "@project-interfaces/tv-channel";
import { TvChannelService } from "@project-services/tv-channel.service";
import { FlwModalComponent } from "../../../ui/modal/flw-modal.component";
import { TranslateModule } from "@ngx-translate/core";

@Component({
  standalone: true,
  imports: [DatePipe, NgFor, NgIf, FlwModalComponent, TranslateModule],
  template: `
    <flw-modal
      [title]="'CHANNEL_DIALOGS.REPORT.TITLE' | translate"
      [description]="data.channelName"
      [wide]="true"
    >
      <div class="empty" *ngIf="loading">
        {{ "CHANNEL_DIALOGS.REPORT.LOADING" | translate }}
      </div>
      <ng-container *ngIf="latest as report">
        <div class="counters">
          <span class="pill critical">{{
            "CHANNEL_DIALOGS.REPORT.ERRORS"
              | translate: { count: report.issue_counts.error }
          }}</span
          ><span class="pill warning">{{
            "CHANNEL_DIALOGS.REPORT.WARNINGS"
              | translate: { count: report.issue_counts.warning }
          }}</span
          ><span class="pill info">{{
            "CHANNEL_DIALOGS.REPORT.INFO"
              | translate: { count: report.issue_counts.info }
          }}</span>
        </div>
        <article
          class="issue"
          *ngFor="let issue of report.issues"
          [class.critical]="issue.severity === 'error'"
        >
          <strong>{{ issue.message }}</strong
          ><small class="mono" *ngIf="issue.starts_at"
            >{{ issue.starts_at | date: "HH:mm" }} –
            {{ issue.ends_at | date: "HH:mm" }}</small
          >
        </article>
      </ng-container>
      <hr class="divider" />
      <span class="section-label">{{
        "CHANNEL_DIALOGS.REPORT.PREVIOUS" | translate
      }}</span>
      <div class="kv">
        <div class="row" *ngFor="let report of reports">
          <span class="k mono">{{
            report.created_at | date: "dd/MM/yyyy HH:mm"
          }}</span
          ><span
            class="v pill"
            [class.critical]="report.issue_counts.error"
            [class.success]="!report.issue_counts.error"
            >{{
              (report.issue_counts.error
                ? "CHANNEL_DIALOGS.REPORT.WITH_ERRORS"
                : "CHANNEL_DIALOGS.REPORT.DONE"
              ) | translate
            }}</span
          >
        </div>
      </div>
      <div modal-footer>
        <span></span
        ><button class="btn" type="button" (click)="ref.close()">
          {{ "CHANNEL_DIALOGS.COMMON.CLOSE" | translate }}
        </button>
      </div>
    </flw-modal>
  `,
  styles: [
    `
      .counters {
        display: flex;
        gap: 8px;
      }
      .issue {
        display: grid;
        gap: 3px;
        padding: 12px;
        border-radius: var(--radius-m);
        background: var(--warning-soft);
      }
      .issue.critical {
        background: var(--critical-soft);
      }
      .issue small {
        color: var(--slate-500);
      }
    `,
  ],
})
export class ReportDialogComponent {
  reports: PlayoutGenerationReport[] = [];
  loading = true;
  constructor(
    service: TvChannelService,
    public ref: DialogRef<void>,
    @Inject(DIALOG_DATA)
    public data: { channelId: string | number; channelName: string },
  ) {
    service.getGenerationReports(data.channelId).subscribe((r) => {
      this.loading = false;
      if (r.isOk) this.reports = r.body as PlayoutGenerationReport[];
    });
  }
  get latest() {
    return this.reports[0] ?? null;
  }
}
