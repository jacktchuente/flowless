import { ChangeDetectionStrategy, Component, Input } from "@angular/core";
import { NgFor } from "@angular/common";

const ICON_PATHS: Record<string, string[]> = {
  dashboard: [
    "M3 3h7v7H3z",
    "M14 3h7v4h-7z",
    "M14 11h7v10h-7z",
    "M3 14h7v7H3z",
  ],
  sources: [
    "M4 5c0-1.1 3.6-2 8-2s8 .9 8 2-3.6 2-8 2-8-.9-8-2Z",
    "M4 5v6c0 1.1 3.6 2 8 2s8-.9 8-2V5",
    "M4 11v6c0 1.1 3.6 2 8 2s8-.9 8-2v-6",
  ],
  collections: ["M3 6h18v14H3z", "M7 3h10l2 3H5z"],
  medias: ["M4 4h16v16H4z", "m4 12 3-3 3 3 3-4 3 4", "M9 9h.01"],
  channels: ["M4 6h16v12H4z", "M9 6l3-3 3 3", "M9 21h6"],
  planning: ["M4 19V5", "M4 12h16", "M8 8h4", "M8 16h8"],
  plus: ["M12 5v14", "M5 12h14"],
  generate: [
    "M12 3v3m0 12v3m9-9h-3M6 12H3m14.4-6.4-2.1 2.1M8.7 15.3l-2.1 2.1m10.8 0-2.1-2.1M8.7 8.7 6.6 6.6",
  ],
  search: ["m21 21-4.3-4.3", "M19 11a8 8 0 1 1-16 0 8 8 0 0 1 16 0Z"],
  filter: ["M4 5h16", "M7 12h10", "M10 19h4"],
  edit: ["M4 20h4L19 9l-4-4L4 16v4Z M15 5l4 4"],
  trash: [
    "M4 7h16",
    "M9 7V4h6v3",
    "M10 11l1 7",
    "M14 11l-1 7",
    "M6 7l1 14h10l1-14",
  ],
  sync: [
    "M20 7h-5V2",
    "M20 7a8 8 0 0 0-14-3",
    "M4 17h5v5",
    "M4 17a8 8 0 0 0 14 3",
  ],
  upload: ["M12 16V4 M5 11l7-7 7 7", "M5 20h14"],
  download: ["M12 4v12 M5 9l7 7 7-7", "M5 20h14"],
  image: ["M4 4h16v16H4z", "m4 12 3-3 3 3 3-4 3 4", "M9 9h.01"],
  report: ["M6 3h9l4 4v14H6z", "M14 3v5h5", "M9 13h6", "M9 17h6"],
  chevron: ["m9 18 6-6-6-6"],
  kebab: ["M12 5h.01", "M12 12h.01", "M12 19h.01"],
  info: ["M12 8h.01", "M11 12h1v4h1", "M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z"],
  warning: ["M12 3 2 20H2L12 3Z", "M12 9v4", "M12 17h.01"],
  close: ["m6 6 12 12", "m18 6-12 12"],
  check: ["m5 12 4 4L19 6"],
  menu: ["M4 7h16", "M4 12h16", "M4 17h16"],
  settings: [
    "M12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6Z",
    "M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 1 1-4 0v-.09a1.65 1.65 0 0 0-1-1.51 1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 1 1 0-4h.09a1.65 1.65 0 0 0 1.51-1 1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33h.09a1.65 1.65 0 0 0 1-1.51V3a2 2 0 1 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82v.09a1.65 1.65 0 0 0 1.51 1H21a2 2 0 1 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1Z",
  ],
};

@Component({
  selector: "flw-icon",
  standalone: true,
  template: `<svg
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    stroke-width="1.8"
    stroke-linecap="round"
    stroke-linejoin="round"
    aria-hidden="true"
  >
    <path *ngFor="let path of paths" [attr.d]="path" />
  </svg>`,
  imports: [NgFor],
  styles: [
    `
      :host {
        display: inline-flex;
        width: 1em;
        height: 1em;
      }
      svg {
        width: 100%;
        height: 100%;
      }
    `,
  ],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class FlwIconComponent {
  @Input() name = "info";
  get paths() {
    return ICON_PATHS[this.name] ?? ICON_PATHS["info"];
  }
}
