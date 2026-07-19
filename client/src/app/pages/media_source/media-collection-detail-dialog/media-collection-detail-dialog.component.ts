import { Component, Inject } from "@angular/core";
import { ReactiveFormsModule, FormControl, FormGroup } from "@angular/forms";
import { DIALOG_DATA, DialogRef } from "@angular/cdk/dialog";
import { TranslateModule, TranslateService } from "@ngx-translate/core";
import { MediaCollection } from "@project-interfaces/media-collection";
import { MediaCollectionService } from "@project-services/media-collection.service";
import { AnalyzeStatus } from "../../../_utils/analyze-status";
import { FlwDialogService } from "../../../ui/dialog.service";
import { FlwConfirmComponent } from "../../../ui/confirm/flw-confirm.component";
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
    private dialogs: FlwDialogService,
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
  // Base sur le role enregistre (pas la valeur du formulaire): l'API
  // verifie le role sauvegarde — il faut enregistrer avant d'analyser.
  get isMainRole() {
    return this.data.collection.programming_role === 1;
  }
  analyze() {
    if (!this.isMainRole) return;
    const collection = this.data.collection;
    const alreadyAnalyzed = !!collection.analyzed_at;
    const isAnalyzing = collection.analyze_status === AnalyzeStatus.Running;
    this.dialogs
      .open(FlwConfirmComponent, {
        data: {
          title: this.translate.instant("MEDIA_COLLECTION.ANALYZE_COLLECTION"),
          message: this.translate.instant("MEDIA_COLLECTION.CONFIRM_ANALYZE", {
            name: collection.name,
          }),
          warning: isAnalyzing
            ? this.translate.instant("MEDIA_COLLECTION.ANALYZING_WARNING")
            : undefined,
          confirmLabel: this.translate.instant("MEDIA_COLLECTION.ANALYZE"),
          extraLabel:
            alreadyAnalyzed || isAnalyzing
              ? this.translate.instant("MEDIA_COLLECTION.FORCE_REANALYZE")
              : undefined,
        },
      })
      .closed.subscribe((result) => {
        if (!result) return;
        this.service
          .analyze(collection.id, result === "extra")
          .subscribe((r) => {
            if (r.isOk) this.ref.close(true);
          });
      });
  }
}
