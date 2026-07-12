import { Component, Inject } from "@angular/core";
import { DatePipe } from "@angular/common";
import { DIALOG_DATA, DialogRef } from "@angular/cdk/dialog";
import { ScheduledMediaItem } from "@project-interfaces/tv-channel";
import { FlwModalComponent } from "../../../ui/modal/flw-modal.component";
import { TranslateModule } from "@ngx-translate/core";
@Component({
  standalone: true,
  imports: [DatePipe, FlwModalComponent, TranslateModule],
  template: `<flw-modal
    [title]="data.item.media_item_title"
    [description]="'CHANNEL_DIALOGS.SCHEDULE.DESC' | translate"
    ><div class="kv">
      <div class="row">
        <span class="k">{{
          "CHANNEL_DIALOGS.SCHEDULE.CONTAINER" | translate
        }}</span
        ><strong class="v">{{ data.item.media_container_title }}</strong>
      </div>
      <div class="row">
        <span class="k">{{
          "CHANNEL_DIALOGS.SCHEDULE.BROADCAST" | translate
        }}</span
        ><strong class="v mono"
          >{{ data.item.starts_at | date: "dd/MM HH:mm" }} –
          {{ data.item.ends_at | date: "HH:mm" }}</strong
        >
      </div>
      <div class="row">
        <span class="k">{{
          "CHANNEL_DIALOGS.SCHEDULE.SELECTION" | translate
        }}</span
        ><strong class="v">{{ data.item.selection_type }}</strong>
      </div>
      <div class="row">
        <span class="k">{{ "CHANNEL_DIALOGS.SCHEDULE.ROLE" | translate }}</span
        ><strong class="v">{{ data.item.role_label || "—" }}</strong>
      </div>
    </div>
    <p>
      {{
        data.item.media_item_description ||
          ("CHANNEL_DIALOGS.SCHEDULE.NO_DESCRIPTION" | translate)
      }}
    </p>
    <div modal-footer>
      <span></span
      ><button class="btn" (click)="ref.close()">
        {{ "CHANNEL_DIALOGS.COMMON.CLOSE" | translate }}
      </button>
    </div></flw-modal
  >`,
})
export class ScheduleDetailDialogComponent {
  constructor(
    public ref: DialogRef<void>,
    @Inject(DIALOG_DATA) public data: { item: ScheduledMediaItem },
  ) {}
}
