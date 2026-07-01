import {Component, DestroyRef, Inject, inject} from '@angular/core';
import {NgFor, NgIf} from "@angular/common";
import {FormsModule} from "@angular/forms";
import {MAT_DIALOG_DATA, MatDialogModule, MatDialogRef} from "@angular/material/dialog";
import {MatButtonModule} from "@angular/material/button";
import {MatCheckboxModule} from "@angular/material/checkbox";
import {MatProgressSpinnerModule} from "@angular/material/progress-spinner";
import {takeUntilDestroyed} from "@angular/core/rxjs-interop";
import {CatalogService} from "@project-services/catalog.service";
import {MediaCollection} from "@project-interfaces/media-collection";
import {MediaCollectionService} from "@project-services/media-collection.service";
import {NotificationService} from "@project-shared/services/notification.service";
import {DialogContainer1Component} from "@project-templates/dialog-container1/dialog-container1.component";

@Component({
  selector: 'app-editorial-planning-generation-dialog',
  standalone: true,
  imports: [
    DialogContainer1Component,
    FormsModule,
    MatButtonModule,
    MatCheckboxModule,
    MatDialogModule,
    MatProgressSpinnerModule,
    NgFor,
    NgIf,
  ],
  templateUrl: './editorial-planning-generation-dialog.component.html',
  styleUrl: './editorial-planning-generation-dialog.component.css'
})
export class EditorialPlanningGenerationDialogComponent {
  private readonly destroyRef = inject(DestroyRef)

  mediaCollections: MediaCollection[] = []
  selectedCollectionIds = new Set<string>()
  targetChannelCount = 2
  maxChannelCandidates = 2
  isSubmitting = false
  errorMessage: string | null = null

  constructor(
    private catalogService: CatalogService,
    private mediaCollectionService: MediaCollectionService,
    private notificationService: NotificationService,
    private dialogRef: MatDialogRef<EditorialPlanningGenerationDialogComponent>,
    @Inject(MAT_DIALOG_DATA) public data: {
      catalogId: string | number,
      catalogName: string,
    },
  ) {
    this.mediaCollectionService.getObjectBehaviorSubject()
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe((collections: MediaCollection[]) => {
        this.mediaCollections = collections.filter((collection) => collection.is_active)
        if (!this.selectedCollectionIds.size) {
          for (const collection of this.mediaCollections) {
            this.selectedCollectionIds.add(collection.id.toString())
          }
        }
      })
    this.mediaCollectionService.listObject(null, true)
  }

  get title(): string {
    return `Programmation flexible de ${this.data.catalogName}`
  }

  isSelected(collection: MediaCollection): boolean {
    return this.selectedCollectionIds.has(collection.id.toString())
  }

  toggleCollection(collection: MediaCollection, checked: boolean) {
    const key = collection.id.toString()
    if (checked) {
      this.selectedCollectionIds.add(key)
      return
    }
    this.selectedCollectionIds.delete(key)
  }

  save() {
    if (this.isSubmitting) {
      return
    }
    const mediaCollectionIds = Array.from(this.selectedCollectionIds)
    if (!mediaCollectionIds.length) {
      this.errorMessage = "Selectionne au moins une collection active."
      return
    }
    this.isSubmitting = true
    this.errorMessage = null
    this.catalogService.generateEditorialPlanning(this.data.catalogId, {
      media_collection_ids: mediaCollectionIds,
      max_channel_candidates: this.maxChannelCandidates,
      target_channel_count: this.targetChannelCount,
    }).subscribe((response) => {
      this.isSubmitting = false
      if (!response.isOk) {
        this.errorMessage = "Generation flexible impossible."
        this.notificationService.notify(this.errorMessage)
        return
      }
      this.dialogRef.close(true)
    })
  }
}
