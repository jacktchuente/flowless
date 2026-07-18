import { Component, Inject } from "@angular/core";
import { Router } from "@angular/router";
import { DIALOG_DATA, DialogRef } from "@angular/cdk/dialog";
import { NgIf } from "@angular/common";
import {
  TvChannelLogoPromptResponse,
  TvChannelService,
} from "@project-services/tv-channel.service";
import { FlwModalComponent } from "../../../ui/modal/flw-modal.component";
import { FlwIconComponent } from "../../../ui/icon/flw-icon.component";
import { TranslateModule } from "@ngx-translate/core";

@Component({
  standalone: true,
  imports: [NgIf, FlwModalComponent, FlwIconComponent, TranslateModule],
  template: `
    <flw-modal
      [title]="'CHANNEL_DIALOGS.LOGO.TITLE' | translate"
      [description]="'CHANNEL_DIALOGS.LOGO.DESC' | translate"
    >
      <div class="preview">
        <img
          *ngIf="data.logo"
          [src]="data.logo"
          [alt]="data.channelName"
        /><span *ngIf="!data.logo">{{ data.channelName.charAt(0) }}</span>
      </div>
      <div class="choices">
        <button class="choice" type="button" (click)="file.click()">
          <flw-icon name="upload" /><strong>{{
            "CHANNEL_DIALOGS.LOGO.UPLOAD" | translate
          }}</strong>
        </button>
        <button class="choice" type="button" (click)="generate('comfyui')">
          <flw-icon name="image" /><strong>{{
            "CHANNEL_DIALOGS.LOGO.LOCAL" | translate
          }}</strong>
        </button>
        <button class="choice" type="button" (click)="generate('openai')">
          <flw-icon name="image" /><strong>{{
            "CHANNEL_DIALOGS.LOGO.CLOUD" | translate
          }}</strong>
        </button>
        <button class="choice" type="button" (click)="openSuggestions()">
          <flw-icon name="search" /><strong>{{
            "CHANNEL_DIALOGS.LOGO.SUGGESTIONS" | translate
          }}</strong>
        </button>
      </div>
      <input
        #file
        hidden
        type="file"
        accept="image/*"
        (change)="upload($event)"
      />
      <p class="tooltip-note">
        {{ "CHANNEL_DIALOGS.LOGO.HINT" | translate }}
      </p>
      <div modal-footer>
        <button class="btn ghost" type="button" (click)="downloadPrompt()">
          <flw-icon name="download" />{{
            "CHANNEL_DIALOGS.LOGO.DOWNLOAD" | translate
          }}</button
        ><button class="btn" type="button" (click)="ref.close(changed)">
          {{ "CHANNEL_DIALOGS.COMMON.CLOSE" | translate }}
        </button>
      </div>
    </flw-modal>
  `,
  styles: [
    `
      .preview {
        width: 128px;
        height: 128px;
        margin: auto;
        display: grid;
        place-items: center;
        border-radius: var(--radius-l);
        background: var(--signal-soft);
        font: 700 42px var(--font-display);
        overflow: hidden;
      }
      .preview img {
        width: 100%;
        height: 100%;
        object-fit: cover;
      }
      .choices {
        display: grid;
        grid-template-columns: repeat(2, 1fr);
        gap: 12px;
      }
      .choice {
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 10px;
        padding: 20px;
        border: 1px solid var(--slate-200);
        border-radius: var(--radius-m);
        background: #fff;
        cursor: pointer;
      }
      .choice flw-icon {
        font-size: 24px;
      }
    `,
  ],
})
export class LogoDialogComponent {
  changed = false;
  constructor(
    private service: TvChannelService,
    private router: Router,
    public ref: DialogRef<boolean>,
    @Inject(DIALOG_DATA)
    public data: {
      channelId: string | number;
      channelName: string;
      logo: string | null;
    },
  ) {}
  openSuggestions() {
    this.ref.close(this.changed);
    this.router.navigate(["/app/channel-images"], {
      queryParams: { channel: this.data.channelId },
    });
  }
  upload(event: Event) {
    const file = (event.target as HTMLInputElement).files?.[0];
    if (file)
      this.service.uploadLogo(this.data.channelId, file).subscribe((r) => {
        if (r.isOk) this.changed = true;
      });
  }
  generate(backend: "comfyui" | "openai") {
    this.service.generateLogo(this.data.channelId, backend).subscribe((r) => {
      if (r.isOk) this.changed = true;
    });
  }
  downloadPrompt() {
    this.service.exportLogoPrompt(this.data.channelId).subscribe((r) => {
      if (!r.isOk) return;
      const prompt = (r.body as TvChannelLogoPromptResponse).prompt;
      const url = URL.createObjectURL(
        new Blob([prompt], { type: "text/plain" }),
      );
      const a = document.createElement("a");
      a.href = url;
      a.download = `${this.data.channelName}-logo-prompt.txt`;
      a.click();
      URL.revokeObjectURL(url);
    });
  }
}
