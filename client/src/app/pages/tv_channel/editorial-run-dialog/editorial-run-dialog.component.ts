import {Component, Inject} from '@angular/core';
import {DatePipe, DecimalPipe, NgFor, NgIf} from "@angular/common";
import {MAT_DIALOG_DATA, MatDialogModule, MatDialogRef} from "@angular/material/dialog";
import {MatButtonModule} from "@angular/material/button";
import {MatCheckboxModule} from "@angular/material/checkbox";
import {MatDialog} from "@angular/material/dialog";
import {MatIconModule} from "@angular/material/icon";
import {MatProgressSpinnerModule} from "@angular/material/progress-spinner";
import {MatTooltipModule} from "@angular/material/tooltip";
import {
  EditorialFlowRun,
  EditorialRunReconciliationProposal,
  EditorialRunReconciliationResponse,
} from "@project-interfaces/editorial-planning";
import {EditorialPlanningService} from "@project-services/editorial-planning.service";
import {ConfirmationDialogComponent} from "@project-shared/confirmation-dialog/confirmation-dialog.component";
import {NotificationService} from "@project-shared/services/notification.service";
import {DialogContainer1Component} from "@project-templates/dialog-container1/dialog-container1.component";

interface SegmentationDiagnostics {
  selected_k?: number
  global_silhouette?: number
  silhouette_scores?: Record<string, number>
  secondary_membership_count?: number
  refinement?: {threshold?: number, dropped_count?: number, kept_count?: number, skipped?: boolean}
}

@Component({
  selector: 'app-editorial-run-dialog',
  standalone: true,
  imports: [
    DatePipe,
    DecimalPipe,
    DialogContainer1Component,
    MatButtonModule,
    MatCheckboxModule,
    MatDialogModule,
    MatIconModule,
    MatProgressSpinnerModule,
    MatTooltipModule,
    NgFor,
    NgIf,
  ],
  templateUrl: './editorial-run-dialog.component.html',
  styleUrl: './editorial-run-dialog.component.css'
})
export class EditorialRunDialogComponent {
  runs: EditorialFlowRun[] = []
  isLoading = true
  isWorking = false
  expandedRunId: string | number | null = null
  reconcileRunId: string | number | null = null
  proposals: EditorialRunReconciliationProposal[] = []
  readonly selectedProposals = new Set<number>()

  constructor(
    private editorialPlanningService: EditorialPlanningService,
    private notificationService: NotificationService,
    private dialog: MatDialog,
    private dialogRef: MatDialogRef<EditorialRunDialogComponent>,
    @Inject(MAT_DIALOG_DATA) public data: {catalogId: string | number, catalogName: string},
  ) {
    this.loadRuns()
  }

  get title(): string {
    return `Runs éditoriaux de ${this.data.catalogName}`
  }

  loadRuns() {
    this.isLoading = true
    this.editorialPlanningService.listRuns(this.data.catalogId).subscribe((response) => {
      this.isLoading = false
      if (!response.isOk) {
        this.notificationService.notify("Chargement des runs impossible.")
        return
      }
      this.runs = response.body as EditorialFlowRun[]
    })
  }

  getStatusLabel(run: EditorialFlowRun): string {
    switch (Number(run.status)) {
      case 1:
        return 'En cours'
      case 2:
        return 'Terminé'
      case 4:
        return 'Erreurs'
      default:
        return 'Inconnu'
    }
  }

  getStatusClass(run: EditorialFlowRun): string {
    switch (Number(run.status)) {
      case 1:
        return 'is-analyzing'
      case 2:
        return 'is-complete'
      case 4:
        return 'is-warning'
      default:
        return 'is-idle'
    }
  }

  getSegmentationDiagnostics(run: EditorialFlowRun): SegmentationDiagnostics {
    return ((run.diagnostics || {})['segmentation'] || {}) as SegmentationDiagnostics
  }

  getSilhouetteEntries(run: EditorialFlowRun): Array<{k: string, value: number}> {
    const scores = this.getSegmentationDiagnostics(run).silhouette_scores || {}
    return Object.entries(scores)
      .map(([k, value]) => ({k, value: Number(value)}))
      .sort((a, b) => Number(a.k) - Number(b.k))
  }

  getDiagnosticCount(run: EditorialFlowRun, key: string): number {
    const value = (run.diagnostics || {})[key]
    return Array.isArray(value) ? value.length : 0
  }

  getPromotedChannels(run: EditorialFlowRun): string[] {
    return (run.channel_candidates || [])
      .filter((candidate) => candidate.tv_channel !== null)
      .map((candidate) => candidate.tv_channel_name || `#${candidate.tv_channel}`)
  }

  toggleDetails(run: EditorialFlowRun) {
    this.expandedRunId = this.expandedRunId === run.id ? null : run.id
  }

  activate(run: EditorialFlowRun) {
    if (this.isWorking) {
      return
    }
    this.isWorking = true
    this.editorialPlanningService.activateRun(run.id).subscribe((response) => {
      this.isWorking = false
      if (!response.isOk) {
        this.notificationService.notify("Activation du run impossible.")
        return
      }
      this.notificationService.notify("Run activé.")
      this.loadRuns()
    })
  }

  deleteRun(run: EditorialFlowRun) {
    if (this.isWorking) {
      return
    }
    this.dialog.open(ConfirmationDialogComponent, {
      width: '520px',
      maxWidth: '92vw',
      data: {
        confirmationMessage: `Supprimer le run #${run.id} et tous ses segments ?`,
      }
    }).afterClosed().subscribe((confirmed) => {
      if (!confirmed) {
        return
      }
      this.isWorking = true
      this.editorialPlanningService.deleteRun(run.id).subscribe((response) => {
        this.isWorking = false
        if (!response.isOk) {
          const body = response.body as {error?: {channels?: string[]}}
          const channels = body?.error?.channels
          this.notificationService.notify(
            channels?.length
              ? `Suppression refusée : chaînes encore rattachées (${channels.join(', ')}).`
              : "Suppression du run impossible."
          )
          return
        }
        this.notificationService.notify("Run supprimé.")
        this.loadRuns()
      })
    })
  }

  openReconciliation(run: EditorialFlowRun) {
    if (this.reconcileRunId === run.id) {
      this.reconcileRunId = null
      return
    }
    this.reconcileRunId = run.id
    this.proposals = []
    this.selectedProposals.clear()
    this.isWorking = true
    this.editorialPlanningService.reconcileRun(run.id).subscribe((response) => {
      this.isWorking = false
      if (!response.isOk) {
        this.notificationService.notify("Calcul des propositions impossible.")
        this.reconcileRunId = null
        return
      }
      const body = response.body as EditorialRunReconciliationResponse
      this.proposals = body.proposals
      for (const proposal of this.proposals) {
        if (proposal.proposed_candidate) {
          this.selectedProposals.add(proposal.tv_channel.id)
        }
      }
    })
  }

  toggleProposal(proposal: EditorialRunReconciliationProposal, checked: boolean) {
    if (checked) {
      this.selectedProposals.add(proposal.tv_channel.id)
      return
    }
    this.selectedProposals.delete(proposal.tv_channel.id)
  }

  applyReconciliation() {
    if (this.isWorking || this.reconcileRunId === null) {
      return
    }
    const mappings = this.proposals
      .filter((proposal) => proposal.proposed_candidate && this.selectedProposals.has(proposal.tv_channel.id))
      .map((proposal) => ({
        tv_channel: proposal.tv_channel.id,
        candidate: proposal.proposed_candidate!.id,
      }))
    if (!mappings.length) {
      this.notificationService.notify("Aucune proposition sélectionnée.")
      return
    }
    this.isWorking = true
    this.editorialPlanningService.reconcileRun(this.reconcileRunId, mappings).subscribe((response) => {
      this.isWorking = false
      if (!response.isOk) {
        this.notificationService.notify("Réconciliation impossible.")
        return
      }
      const body = response.body as EditorialRunReconciliationResponse
      this.notificationService.notify(`${body.applied.length} chaîne(s) réconciliée(s).`)
      this.proposals = body.proposals
      this.selectedProposals.clear()
      this.loadRuns()
    })
  }

  close() {
    this.dialogRef.close()
  }
}
