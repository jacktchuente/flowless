import {Component, Inject, OnInit} from '@angular/core';
import {DecimalPipe, NgFor, NgIf} from "@angular/common";
import {MAT_DIALOG_DATA, MatDialogModule} from "@angular/material/dialog";
import {MatButtonModule} from "@angular/material/button";
import {MatIconModule} from "@angular/material/icon";
import {MatProgressSpinnerModule} from "@angular/material/progress-spinner";
import {MatTooltipModule} from "@angular/material/tooltip";
import {EditorialSegment, EditorialSegmentMembership} from "@project-interfaces/editorial-planning";
import {EditorialPlanningService} from "@project-services/editorial-planning.service";
import {NotificationService} from "@project-shared/services/notification.service";
import {DialogContainer1Component} from "@project-templates/dialog-container1/dialog-container1.component";

@Component({
  selector: 'app-editorial-membership-review-dialog',
  standalone: true,
  imports: [
    DecimalPipe,
    DialogContainer1Component,
    MatButtonModule,
    MatDialogModule,
    MatIconModule,
    MatProgressSpinnerModule,
    MatTooltipModule,
    NgFor,
    NgIf,
  ],
  templateUrl: './editorial-membership-review-dialog.component.html',
  styleUrl: './editorial-membership-review-dialog.component.css'
})
export class EditorialMembershipReviewDialogComponent implements OnInit {
  segments: EditorialSegment[] = []
  memberships: EditorialSegmentMembership[] = []
  selectedSegment: EditorialSegment | null = null
  isLoadingSegments = false
  isLoadingMemberships = false
  readonly updatingIds = new Set<string>()
  errorMessage: string | null = null

  constructor(
    private editorialPlanningService: EditorialPlanningService,
    private notificationService: NotificationService,
    @Inject(MAT_DIALOG_DATA) public data: {
      catalogId: string | number,
      catalogName: string,
    },
  ) {}

  ngOnInit() {
    this.loadSegments()
  }

  get title(): string {
    return `Revue des segments de ${this.data.catalogName}`
  }

  selectSegment(segment: EditorialSegment) {
    if (this.selectedSegment?.id === segment.id) {
      return
    }
    this.selectedSegment = segment
    this.loadMemberships(segment)
  }

  setStatus(membership: EditorialSegmentMembership, status: string) {
    const key = membership.id.toString()
    if (this.updatingIds.has(key) || membership.status === status) {
      return
    }
    this.updatingIds.add(key)
    this.editorialPlanningService.setMembershipStatus(membership.id, status).subscribe((response) => {
      this.updatingIds.delete(key)
      if (!response.isOk) {
        this.notificationService.notify("Mise a jour du membership impossible.")
        return
      }
      const updated = response.body as EditorialSegmentMembership
      membership.status = updated.status
      membership.decision_reason = updated.decision_reason
    })
  }

  isUpdating(membership: EditorialSegmentMembership): boolean {
    return this.updatingIds.has(membership.id.toString())
  }

  getStatusClass(membership: EditorialSegmentMembership): string {
    switch (membership.status) {
      case 'accepted':
        return 'is-accepted'
      case 'manual_override':
        return 'is-override'
      case 'rejected':
        return 'is-rejected'
      case 'secondary':
        return 'is-secondary'
      default:
        return 'is-other'
    }
  }

  isPlayable(membership: EditorialSegmentMembership): boolean {
    return membership.status === 'accepted' || membership.status === 'manual_override'
  }

  getDominantCategories(segment: EditorialSegment): string {
    const values = (segment.profile?.['dominant_categories'] as string[] | undefined) ?? []
    return values.join(', ')
  }

  private loadSegments() {
    this.isLoadingSegments = true
    this.errorMessage = null
    this.editorialPlanningService.listSegmentsForCatalog(this.data.catalogId).subscribe((response) => {
      this.isLoadingSegments = false
      if (!response.isOk) {
        this.errorMessage = "Chargement des segments impossible."
        return
      }
      this.segments = response.body as EditorialSegment[]
      if (this.segments.length) {
        this.selectSegment(this.segments[0])
      }
    })
  }

  private loadMemberships(segment: EditorialSegment) {
    this.isLoadingMemberships = true
    this.memberships = []
    this.editorialPlanningService.listMemberships(segment.id).subscribe((response) => {
      this.isLoadingMemberships = false
      if (!response.isOk) {
        this.errorMessage = "Chargement des memberships impossible."
        return
      }
      this.memberships = response.body as EditorialSegmentMembership[]
    })
  }
}
