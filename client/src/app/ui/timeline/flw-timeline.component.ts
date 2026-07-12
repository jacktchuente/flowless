import { Component, EventEmitter, Input, Output } from "@angular/core";
import { NgFor, NgIf } from "@angular/common";
import { CATEGORY_COLOR, CategoryKey } from "../category";
export interface TimelineBlock {
  start: string;
  end: string;
  title: string;
  sub?: string;
  category: CategoryKey;
  tooltip?: string;
}
@Component({
  selector: "flw-timeline",
  standalone: true,
  imports: [NgFor, NgIf],
  template: `<div class="timeline" [style.height.px]="height">
    <div
      class="hour"
      *ngFor="let hour of hours"
      [style.top.px]="(hour - startHour) * pxPerHour"
    >
      <span class="mono">{{ pad(hour % 24) }}:00</span><i></i>
    </div>
    <button
      type="button"
      class="block"
      *ngFor="let block of blocks"
      [style.top.px]="top(block)"
      [style.height.px]="blockHeight(block)"
      [style.background]="color(block).bg"
      [style.color]="color(block).fg"
      [style.border-left-color]="color(block).sw"
      [title]="block.tooltip || ''"
      (click)="blockClick.emit(block)"
    >
      <strong>{{ block.title }}</strong
      ><small class="mono" *ngIf="blockHeight(block) > 34"
        >{{ block.start }} – {{ block.end
        }}<span *ngIf="block.sub"> · {{ block.sub }}</span></small
      >
    </button>
  </div>`,
  styles: [
    `
      :host {
        display: block;
        overflow-y: auto;
      }
      .timeline {
        position: relative;
        min-width: 180px;
      }
      .hour {
        position: absolute;
        left: 0;
        right: 0;
        display: flex;
        gap: 8px;
      }
      .hour span {
        width: 44px;
        flex: none;
        font-size: 11px;
        color: var(--slate-400);
        transform: translateY(-7px);
      }
      .hour i {
        flex: 1;
        border-top: 1px solid var(--slate-100);
      }
      .block {
        position: absolute;
        left: 52px;
        right: 6px;
        border: 0;
        border-left: 3px solid;
        border-radius: 8px;
        padding: 6px 10px;
        overflow: hidden;
        text-align: left;
        cursor: pointer;
      }
      .block strong {
        display: block;
        font-size: 12px;
        line-height: 1.25;
      }
      .block small {
        display: block;
        font-size: 10.5px;
        margin-top: 2px;
      }
    `,
  ],
})
export class FlwTimelineComponent {
  @Input() blocks: TimelineBlock[] = [];
  @Input() startHour = 0;
  @Input() endHour = 24;
  @Input() pxPerHour = 64;
  @Output() blockClick = new EventEmitter<TimelineBlock>();
  get height() {
    return (this.endHour - this.startHour) * this.pxPerHour;
  }
  get hours() {
    return Array.from(
      { length: this.endHour - this.startHour + 1 },
      (_, i) => this.startHour + i,
    );
  }
  pad(v: number) {
    return String(v).padStart(2, "0");
  }
  minutes(time: string) {
    const [h, m] = time.split(":").map(Number);
    let result = h * 60 + (m || 0);
    if (result < this.startHour * 60) result += 1440;
    return result;
  }
  top(b: TimelineBlock) {
    return (
      ((this.minutes(b.start) - this.startHour * 60) / 60) * this.pxPerHour
    );
  }
  blockHeight(b: TimelineBlock) {
    let duration = this.minutes(b.end) - this.minutes(b.start);
    if (duration <= 0) duration += 1440;
    return Math.max((duration / 60) * this.pxPerHour - 3, 16);
  }
  color(b: TimelineBlock) {
    return CATEGORY_COLOR[b.category] ?? CATEGORY_COLOR.filler;
  }
}
