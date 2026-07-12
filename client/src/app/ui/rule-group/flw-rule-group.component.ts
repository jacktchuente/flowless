import { Component, Input } from "@angular/core";
import { NgIf } from "@angular/common";
@Component({
  selector: "flw-rule-group",
  standalone: true,
  imports: [NgIf],
  template: `<section class="rule-group" [class]="kind">
    <div class="rg-head">
      <span class="lbl">{{ label }}</span
      ><span class="hint" *ngIf="hint">{{ hint }}</span>
    </div>
    <ng-content />
  </section>`,
  styles: [
    `
      .hint {
        font-size: 11.5px;
        color: var(--slate-500);
      }
    `,
  ],
})
export class FlwRuleGroupComponent {
  @Input() kind: "allow" | "prefer" | "forbid" = "allow";
  @Input() label = "";
  @Input() hint = "";
}
