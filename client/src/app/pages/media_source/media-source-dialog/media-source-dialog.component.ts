import { Component, Inject } from "@angular/core";
import { NgIf } from "@angular/common";
import {
  FormControl,
  FormGroup,
  ReactiveFormsModule,
  Validators,
} from "@angular/forms";
import { DIALOG_DATA, DialogRef } from "@angular/cdk/dialog";
import {
  MediaSource,
  MediaSourcePayload,
} from "@project-interfaces/media-source";
import { MediaSourceService } from "@project-services/media-source.service";
import { FlwModalComponent } from "../../../ui/modal/flw-modal.component";
@Component({
  standalone: true,
  imports: [NgIf, ReactiveFormsModule, FlwModalComponent],
  templateUrl: "./media-source-dialog.component.html",
  styleUrl: "./media-source-dialog.component.css",
})
export class MediaSourceDialogComponent {
  isSubmitting = false;
  errorMessage = "";
  form = new FormGroup({
    name: new FormControl(this.data.source?.name ?? "", {
      nonNullable: true,
      validators: [Validators.required],
    }),
    application_url: new FormControl(
      this.data.source?.credentials.application_url ?? "",
      { nonNullable: true, validators: [Validators.required] },
    ),
    username: new FormControl(this.data.source?.credentials.username ?? "", {
      nonNullable: true,
    }),
    password: new FormControl(this.data.source?.credentials.password ?? "", {
      nonNullable: true,
    }),
  });
  constructor(
    private service: MediaSourceService,
    public ref: DialogRef<boolean>,
    @Inject(DIALOG_DATA) public data: { source?: MediaSource },
  ) {}
  save() {
    if (this.form.invalid || this.isSubmitting) {
      this.form.markAllAsTouched();
      return;
    }
    this.isSubmitting = true;
    this.errorMessage = "";
    const v = this.form.getRawValue();
    const payload: MediaSourcePayload = {
      name: v.name,
      source_type: this.data.source?.source_type ?? 1,
      credentials: {
        application_url: v.application_url,
        username: v.username,
        password: v.password,
      },
    };
    this.service.verifyCredentials(payload).subscribe((verify) => {
      if (!verify.isOk) {
        this.isSubmitting = false;
        this.errorMessage = this.error(verify.body);
        return;
      }
      const request = this.data.source
        ? this.service.patchObject(String(this.data.source.id), payload)
        : this.service.createObject(payload);
      request.subscribe((result) => {
        this.isSubmitting = false;
        if (!result.isOk) {
          this.errorMessage = this.error(result.body);
          return;
        }
        this.ref.close(true);
      });
    });
  }
  private error(value: unknown) {
    const e = value as any;
    return (
      e?.error?.credentials?.[0] ??
      e?.error?.detail ??
      e?.message ??
      "La connexion à la source a échoué."
    );
  }
}
