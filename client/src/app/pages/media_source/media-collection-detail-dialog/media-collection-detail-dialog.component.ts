import { Component, Inject } from "@angular/core";
import { ReactiveFormsModule, FormControl, FormGroup } from "@angular/forms";
import { DIALOG_DATA, DialogRef } from "@angular/cdk/dialog";
import { TranslateModule, TranslateService } from "@ngx-translate/core";
import { MediaCollection } from "@project-interfaces/media-collection";
import { MediaCollectionService } from "@project-services/media-collection.service";
import { FlwModalComponent } from "../../../ui/modal/flw-modal.component";
import { FlwSelectComponent } from "../../../ui/select/flw-select.component";
import { FlwSwitchComponent } from "../../../ui/switch/flw-switch.component";
import {
  ROLES,
  NATURES,
  KINDS,
} from "../media-collection/media-collection.component";
@Component({
  standalone: true,
  imports: [
    ReactiveFormsModule,
    TranslateModule,
    FlwModalComponent,
    FlwSelectComponent,
    FlwSwitchComponent,
  ],
  templateUrl: "./media-collection-detail-dialog.component.html",
  styleUrl: "./media-collection-detail-dialog.component.css",
})
export class MediaCollectionDetailDialogComponent {
  isSubmitting = false;
  readonly roleOptions = this.optionsFor(ROLES);
  readonly natureOptions = this.optionsFor(NATURES);
  readonly kindOptions = this.optionsFor(KINDS);
  form = new FormGroup({
    programming_role: new FormControl(this.data.collection.programming_role),
    nature: new FormControl(this.data.collection.nature),
    container_kind: new FormControl(this.data.collection.container_kind),
    is_anime: new FormControl(!!this.data.collection.is_anime, {
      nonNullable: true,
    }),
  });
  constructor(
    private service: MediaCollectionService,
    private translate: TranslateService,
    public ref: DialogRef<boolean>,
    @Inject(DIALOG_DATA) public data: { collection: MediaCollection },
  ) {}
  private optionsFor(options: { value: number; label: string }[]) {
    return [
      { label: "—", value: null as number | null },
      ...options.map((o) => ({
        value: o.value as number | null,
        label: this.translate.instant(o.label),
      })),
    ];
  }
  save() {
    this.isSubmitting = true;
    this.service
      .patchObject(String(this.data.collection.id), this.form.getRawValue())
      .subscribe((r) => {
        this.isSubmitting = false;
        if (r.isOk) this.ref.close(true);
      });
  }
  analyze() {
    this.service
      .analyze(this.data.collection.id, !!this.data.collection.analyzed_at)
      .subscribe((r) => {
        if (r.isOk) this.ref.close(true);
      });
  }
}
