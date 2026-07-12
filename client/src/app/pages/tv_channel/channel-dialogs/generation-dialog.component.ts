import { NgIf } from "@angular/common";
import { Component, DestroyRef, Inject, inject } from "@angular/core";
import { DIALOG_DATA, DialogRef } from "@angular/cdk/dialog";
import { FormsModule } from "@angular/forms";
import { filter } from "rxjs";
import { takeUntilDestroyed } from "@angular/core/rxjs-interop";
import { WebsocketService } from "@kwyxyz/ngx-request";
import { TvChannelService } from "@project-services/tv-channel.service";
import { FlwModalComponent } from "../../../ui/modal/flw-modal.component";
import { FlwSwitchComponent } from "../../../ui/switch/flw-switch.component";
import { FlwSelectComponent } from "../../../ui/select/flw-select.component";
import { FlwGenStepsComponent } from "../../../ui/gen-steps/flw-gen-steps.component";

export interface GenerationDialogData {
  channelId: string | number;
  channelName: string;
  kind: "blueprint" | "playout";
}

@Component({
  standalone: true,
  imports: [
    NgIf,
    FormsModule,
    FlwModalComponent,
    FlwSwitchComponent,
    FlwSelectComponent,
    FlwGenStepsComponent,
  ],
  template: `
    <flw-modal [title]="title" [description]="description">
      <ng-container *ngIf="state === 'idle'">
        <ng-container *ngIf="data.kind === 'blueprint'; else playoutFields">
          <div class="field">
            <label>Méthode</label
            ><flw-select [(ngModel)]="method" [options]="methods" />
          </div>
          <flw-switch [(ngModel)]="gridOnly" label="Grille seule" />
          <flw-switch [(ngModel)]="reboot" label="Forcer le redémarrage" />
        </ng-container>
        <ng-template #playoutFields>
          <div class="field">
            <label>Nombre de jours</label
            ><input
              class="mono"
              type="number"
              min="1"
              max="31"
              [(ngModel)]="days"
            />
          </div>
          <flw-switch
            [(ngModel)]="reset"
            label="Réinitialiser le planning existant"
          />
        </ng-template>
      </ng-container>
      <flw-gen-steps *ngIf="state !== 'idle'" [steps]="steps" [state]="state" />
      <p class="tooltip-note amber" *ngIf="state === 'error'">
        La génération a échoué ou n’a pas confirmé sa fin dans le délai attendu.
      </p>
      <div modal-footer>
        <span></span>
        <div class="actions">
          <button
            class="btn ghost"
            type="button"
            (click)="ref.close(state === 'done')"
          >
            {{ state === "running" ? "Masquer" : "Fermer" }}
          </button>
          <button
            class="btn primary"
            type="button"
            *ngIf="state === 'idle'"
            (click)="start()"
          >
            Lancer la génération
          </button>
        </div>
      </div>
    </flw-modal>
  `,
  styles: [
    `
      .actions {
        display: flex;
        gap: 8px;
      }
    `,
  ],
})
export class GenerationDialogComponent {
  private destroyRef = inject(DestroyRef);
  state: "idle" | "running" | "done" | "error" = "idle";
  method: "full_llm" | "random" | "preset_and_llm" = "preset_and_llm";
  methods = [
    { label: "Assistée par IA", value: "full_llm" },
    { label: "Modèle prédéfini", value: "preset_and_llm" },
    { label: "Aléatoire", value: "random" },
  ];
  gridOnly = false;
  reboot = false;
  days = 7;
  reset = false;
  private timeout?: ReturnType<typeof setTimeout>;

  constructor(
    private service: TvChannelService,
    ws: WebsocketService,
    public ref: DialogRef<boolean>,
    @Inject(DIALOG_DATA) public data: GenerationDialogData,
  ) {
    ws.crudEvent
      .pipe(
        filter(
          (event: any) =>
            event.type?.toLowerCase?.() === "tvchannel" &&
            String(event.id) === String(data.channelId),
        ),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe(() => {
        if (this.state === "running") {
          this.state = "done";
          if (this.timeout) clearTimeout(this.timeout);
        }
      });
  }

  get title() {
    return this.data.kind === "blueprint"
      ? "Générer le plan"
      : "Générer le planning";
  }
  get description() {
    return `Chaîne — ${this.data.channelName}`;
  }
  get steps() {
    return this.data.kind === "blueprint"
      ? [
          "Lecture des collections",
          "Construction des blocs",
          "Vérification des règles",
          "Écriture de la grille",
        ]
      : [
          "Lecture des règles",
          "Sélection des médias",
          "Résolution des conflits",
          "Écriture du planning",
        ];
  }

  start() {
    this.state = "running";
    const request =
      this.data.kind === "blueprint"
        ? this.service.generateBlueprint(this.data.channelId, {
            grid_generation_mode: this.method,
            grid_only: this.gridOnly,
            reboot: this.reboot,
          })
        : this.service.generatePlayout(this.data.channelId, {
            days: this.days,
            reset: this.reset,
          });
    request.subscribe((response) => {
      if (!response.isOk) this.state = "error";
    });
    this.timeout = setTimeout(
      () => {
        if (this.state === "running") this.state = "error";
      },
      15 * 60 * 1000,
    );
  }
}
