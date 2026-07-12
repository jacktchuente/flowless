import {
  Component,
  Input,
  OnChanges,
  OnDestroy,
  SimpleChanges,
} from "@angular/core";
import { NgFor } from "@angular/common";
import { TranslateService } from "@ngx-translate/core";
@Component({
  selector: "flw-gen-steps",
  standalone: true,
  imports: [NgFor],
  template: `<div class="gen-steps">
    <div class="progress-track"><span [style.width.%]="progress"></span></div>
    <div
      class="gen-step"
      *ngFor="let step of steps; let i = index"
      [class.done]="isDone(i)"
      [class.active]="isActive(i)"
    >
      <span class="mark"></span><span>{{ step }}</span>
    </div>
    <p class="gen-status mono">{{ status }}</p>
  </div>`,
  styles: [
    `
      .gen-status {
        font-size: 11.5px;
        color: var(--slate-500);
      }
    `,
  ],
})
export class FlwGenStepsComponent implements OnChanges, OnDestroy {
  constructor(private translate: TranslateService) {}
  @Input() steps: string[] = [];
  @Input() state: "idle" | "running" | "done" | "error" = "idle";
  index = -1;
  private timer?: ReturnType<typeof setInterval>;
  get progress() {
    if (this.state === "done") return 100;
    if (this.index < 0 || !this.steps.length) return 0;
    return Math.round(((this.index + 1) / this.steps.length) * 100);
  }
  get status() {
    if (this.state === "done")
      return this.translate.instant("UI.GEN_STEPS.DONE");
    if (this.state === "error")
      return this.translate.instant("UI.GEN_STEPS.ERROR");
    return this.index >= 0 ? this.steps[this.index] : "";
  }
  isDone(i: number) {
    return this.state === "done" || i < this.index;
  }
  isActive(i: number) {
    return this.state === "running" && i === this.index;
  }
  ngOnChanges(c: SimpleChanges) {
    if (c["state"]) this.restart();
  }
  restart() {
    this.clear();
    if (this.state === "done") this.index = this.steps.length;
    if (this.state === "idle" || this.state === "error") this.index = -1;
    if (this.state === "running") {
      this.index = 0;
      this.timer = setInterval(() => {
        if (this.index < this.steps.length - 1) this.index++;
      }, 700);
    }
  }
  ngOnDestroy() {
    this.clear();
  }
  private clear() {
    if (this.timer) clearInterval(this.timer);
  }
}
