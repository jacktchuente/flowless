import {Component, Inject} from '@angular/core';
import {FormGroup, ReactiveFormsModule} from "@angular/forms";
import {NgIf} from "@angular/common";
import {MAT_DIALOG_DATA, MatDialogModule, MatDialogRef} from "@angular/material/dialog";
import {MatButtonModule} from "@angular/material/button";
import {MatProgressSpinnerModule} from "@angular/material/progress-spinner";
import {FormlyFieldConfig, FormlyModule} from "@ngx-formly/core";
import {Catalog, CatalogPayload} from "@project-interfaces/catalog";
import {CatalogService} from "@project-services/catalog.service";
import {NotificationService} from "@project-shared/services/notification.service";
import {DialogContainer1Component} from "@project-templates/dialog-container1/dialog-container1.component";

@Component({
  selector: 'app-catalog-dialog',
  standalone: true,
  imports: [
    DialogContainer1Component,
    FormlyModule,
    MatButtonModule,
    MatDialogModule,
    MatProgressSpinnerModule,
    NgIf,
    ReactiveFormsModule
  ],
  templateUrl: './catalog-dialog.component.html',
  styleUrl: './catalog-dialog.component.css'
})
export class CatalogDialogComponent {
  readonly form = new FormGroup({})
  readonly model: CatalogPayload
  readonly fields: FormlyFieldConfig[] = [
    {
      key: 'name',
      type: 'input',
      props: {
        label: 'Nom',
        required: true,
      }
    },
    {
      key: 'description',
      type: 'textarea',
      props: {
        label: 'Description',
        rows: 4,
      }
    }
  ]

  isSubmitting = false
  errorMessage: string | null = null

  constructor(
    private catalogService: CatalogService,
    private notificationService: NotificationService,
    private dialogRef: MatDialogRef<CatalogDialogComponent>,
    @Inject(MAT_DIALOG_DATA) public data: { catalog?: Catalog }
  ) {
    this.model = {
      name: data.catalog?.name ?? '',
      description: data.catalog?.description ?? '',
    }
  }

  save() {
    if (this.form.invalid || this.isSubmitting) {
      this.form.markAllAsTouched()
      return
    }
    this.isSubmitting = true

    const request = this.data.catalog
      ? this.catalogService.patchObject(this.data.catalog.id.toString(), this.model)
      : this.catalogService.createObject(this.model)

    request.subscribe((response) => {
      this.isSubmitting = false
      if (!response.isOk) {
        this.errorMessage = "Enregistrement impossible."
        this.notificationService.notify(this.errorMessage)
        return
      }
      this.dialogRef.close(true)
    })
  }
}
