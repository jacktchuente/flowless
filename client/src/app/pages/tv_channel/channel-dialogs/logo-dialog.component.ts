import { Component, Inject } from "@angular/core";
import { DIALOG_DATA, DialogRef } from "@angular/cdk/dialog";
import { NgIf } from "@angular/common";
import {
  TvChannelLogoPromptResponse,
  TvChannelService,
} from "@project-services/tv-channel.service";
import { FlwModalComponent } from "../../../ui/modal/flw-modal.component";
import { FlwIconComponent } from "../../../ui/icon/flw-icon.component";

@Component({
  standalone: true,
  imports: [NgIf, FlwModalComponent, FlwIconComponent],
  template: `
    <flw-modal
      title="Logo de la chaîne"
      description="Importez une image ou lancez une génération."
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
          <flw-icon name="upload" /><strong>Importer un fichier</strong>
        </button>
        <button class="choice" type="button" (click)="generate('comfyui')">
          <flw-icon name="image" /><strong>Générer localement</strong>
        </button>
        <button class="choice" type="button" (click)="generate('openai')">
          <flw-icon name="image" /><strong>Générer avec l’IA</strong>
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
        Le prompt utilisé reste disponible après la génération.
      </p>
      <div modal-footer>
        <button class="btn ghost" type="button" (click)="downloadPrompt()">
          <flw-icon name="download" />Télécharger le prompt</button
        ><button class="btn" type="button" (click)="ref.close(changed)">
          Fermer
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
        grid-template-columns: repeat(3, 1fr);
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
    public ref: DialogRef<boolean>,
    @Inject(DIALOG_DATA)
    public data: {
      channelId: string | number;
      channelName: string;
      logo: string | null;
    },
  ) {}
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
