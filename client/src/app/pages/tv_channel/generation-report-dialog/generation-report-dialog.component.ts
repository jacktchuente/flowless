import {Component, Inject, OnInit} from '@angular/core';
import {DatePipe, NgClass, NgFor, NgIf} from "@angular/common";
import {MAT_DIALOG_DATA, MatDialogModule} from "@angular/material/dialog";
import {MatButtonModule} from "@angular/material/button";
import {MatIconModule} from "@angular/material/icon";
import {MatProgressSpinnerModule} from "@angular/material/progress-spinner";
import {PlayoutGenerationIssue, PlayoutGenerationReport} from "@project-interfaces/tv-channel";
import {TvChannelApiService} from "@project-services/tv-channel.service";
import {DialogContainer1Component} from "@project-templates/dialog-container1/dialog-container1.component";

@Component({
  selector: 'app-generation-report-dialog',
  standalone: true,
  imports: [
    DialogContainer1Component,
    MatDialogModule,
    MatButtonModule,
    MatIconModule,
    MatProgressSpinnerModule,
    NgFor,
    NgIf,
    NgClass,
    DatePipe,
  ],
  templateUrl: './generation-report-dialog.component.html',
  styleUrl: './generation-report-dialog.component.css'
})
export class GenerationReportDialogComponent implements OnInit {
  reports: PlayoutGenerationReport[] = []
  expandedReportId: string | number | null = null
  isLoading = true

  constructor(
    @Inject(MAT_DIALOG_DATA) public data: { channelId: string | number, channelName: string },
    private tvChannelApiService: TvChannelApiService,
  ) {
  }

  ngOnInit() {
    this.tvChannelApiService.getGenerationReports(this.data.channelId).subscribe({
      next: (reports) => {
        this.reports = reports
        if (reports.length) {
          this.expandedReportId = reports[0].id
        }
        this.isLoading = false
      },
      error: () => {
        this.isLoading = false
      },
    })
  }

  toggleReport(report: PlayoutGenerationReport) {
    this.expandedReportId = this.expandedReportId === report.id ? null : report.id
  }

  issuesOf(report: PlayoutGenerationReport): PlayoutGenerationIssue[] {
    return report.issues ?? []
  }

  severityIcon(severity: string): string {
    if (severity === 'error') {
      return 'error'
    }
    if (severity === 'warning') {
      return 'warning'
    }
    return 'info'
  }
}
