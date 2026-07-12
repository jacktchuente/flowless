import { Component, Inject } from "@angular/core";
import {
  FormControl,
  FormGroup,
  ReactiveFormsModule,
  Validators,
} from "@angular/forms";
import { DIALOG_DATA, DialogRef } from "@angular/cdk/dialog";
import { Catalog } from "@project-interfaces/catalog";
import { CatalogService } from "@project-services/catalog.service";
import { FlwModalComponent } from "../../../ui/modal/flw-modal.component";
import { TranslateModule } from "@ngx-translate/core";
@Component({
  standalone: true,
  imports: [ReactiveFormsModule, FlwModalComponent, TranslateModule],
  template: `<flw-modal
    [title]="
      (data.catalog ? 'CHANNELS.EDIT_CATALOG' : 'CHANNELS.NEW_CATALOG')
        | translate
    "
    ><form [formGroup]="form">
      <div class="field">
        <label>{{ "COMMON.NAME" | translate }}</label
        ><input formControlName="name" type="text" />
      </div>
      <div class="field">
        <label>{{ "COMMON.DESCRIPTION" | translate }}</label
        ><textarea formControlName="description" rows="4"></textarea>
      </div>
    </form>
    <div modal-footer>
      <span></span>
      <div>
        <button class="btn ghost" (click)="ref.close()">
          {{ "COMMON.CANCEL" | translate }}</button
        ><button class="btn primary" (click)="save()">
          {{ "CHANNEL_DIALOGS.COMMON.SAVE" | translate }}
        </button>
      </div>
    </div></flw-modal
  >`,
  styles: [
    `
      form {
        display: grid;
        gap: 14px;
      }
    `,
  ],
})
export class CatalogDialogComponent {
  form = new FormGroup({
    name: new FormControl(this.data.catalog?.name ?? "", {
      nonNullable: true,
      validators: [Validators.required],
    }),
    description: new FormControl(this.data.catalog?.description ?? ""),
  });
  constructor(
    private service: CatalogService,
    public ref: DialogRef<boolean>,
    @Inject(DIALOG_DATA) public data: { catalog?: Catalog },
  ) {}
  save() {
    if (this.form.invalid) return;
    const req = this.data.catalog
      ? this.service.patchObject(
          String(this.data.catalog.id),
          this.form.getRawValue(),
        )
      : this.service.createObject(this.form.getRawValue());
    req.subscribe((r) => {
      if (r.isOk) this.ref.close(true);
    });
  }
}
