import {Component, Inject, OnInit} from '@angular/core';
import {DecimalPipe, NgFor, NgIf} from "@angular/common";
import {FormsModule} from "@angular/forms";
import {MAT_DIALOG_DATA, MatDialogModule, MatDialogRef} from "@angular/material/dialog";
import {MatButtonModule} from "@angular/material/button";
import {MatIconModule} from "@angular/material/icon";
import {MatProgressSpinnerModule} from "@angular/material/progress-spinner";
import {EditorialChannelCandidate} from "@project-interfaces/editorial-planning";
import {EditorialPlanningService} from "@project-services/editorial-planning.service";
import {NotificationService} from "@project-shared/services/notification.service";
import {DialogContainer1Component} from "@project-templates/dialog-container1/dialog-container1.component";

@Component({
  selector: 'app-editorial-candidate-dialog',
  standalone: true,
  imports: [
    DecimalPipe,
    DialogContainer1Component,
    FormsModule,
    MatButtonModule,
    MatDialogModule,
    MatIconModule,
    MatProgressSpinnerModule,
    NgFor,
    NgIf,
  ],
  templateUrl: './editorial-candidate-dialog.component.html',
  styleUrl: './editorial-candidate-dialog.component.css'
})
export class EditorialCandidateDialogComponent implements OnInit {
  candidates: EditorialChannelCandidate[] = []
  selectedCandidate: EditorialChannelCandidate | null = null
  channelName = ""
  isLoading = false
  isSubmitting = false
  errorMessage: string | null = null

  constructor(
    private editorialPlanningService: EditorialPlanningService,
    private notificationService: NotificationService,
    private dialogRef: MatDialogRef<EditorialCandidateDialogComponent>,
    @Inject(MAT_DIALOG_DATA) public data: {
      catalogId: string | number,
      catalogName: string,
    },
  ) {}

  ngOnInit() {
    this.loadCandidates()
  }

  get title(): string {
    return `Candidates flexibles de ${this.data.catalogName}`
  }

  selectCandidate(candidate: EditorialChannelCandidate) {
    this.selectedCandidate = candidate
    this.channelName = candidate.name.slice(0, 50)
  }

  createChannel() {
    if (!this.selectedCandidate || this.isSubmitting) {
      return
    }
    this.isSubmitting = true
    this.errorMessage = null
    this.editorialPlanningService.createFlexibleChannel(this.selectedCandidate.id, this.channelName).subscribe((response) => {
      this.isSubmitting = false
      if (!response.isOk) {
        this.errorMessage = "Creation de chaine flexible impossible."
        this.notificationService.notify(this.errorMessage)
        return
      }
      this.dialogRef.close(true)
    })
  }

  private loadCandidates() {
    this.isLoading = true
    this.errorMessage = null
    this.editorialPlanningService.listCandidates({catalog: this.data.catalogId}).subscribe((response) => {
      this.isLoading = false
      if (!response.isOk) {
        this.errorMessage = "Chargement des candidates impossible."
        return
      }
      this.candidates = (response.body as EditorialChannelCandidate[])
        .filter((candidate) => !candidate.tv_channel && candidate.segment_path?.elements?.length)
      if (this.candidates.length) {
        this.selectCandidate(this.candidates[0])
      }
    })
  }
}
