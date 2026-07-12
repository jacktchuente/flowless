import { Pipe, PipeTransform } from "@angular/core";
import { TranslateService } from "@ngx-translate/core";
@Pipe({ name: "flwTimeAgo", standalone: true, pure: false })
export class TimeAgoPipe implements PipeTransform {
  constructor(private translate: TranslateService) {}

  transform(value: string | Date | null | undefined): string {
    if (!value) return "—";
    const ms = Date.now() - new Date(value).getTime();
    if (!Number.isFinite(ms)) return "—";
    const mins = Math.max(0, Math.floor(ms / 60000));
    if (mins < 1) return this.translate.instant("UI.TIME_AGO.NOW");
    if (mins < 60)
      return this.translate.instant("UI.TIME_AGO.MINUTES", { count: mins });
    const hours = Math.floor(mins / 60);
    if (hours < 24)
      return this.translate.instant("UI.TIME_AGO.HOURS", { count: hours });
    const days = Math.floor(hours / 24);
    return this.translate.instant("UI.TIME_AGO.DAYS", { count: days });
  }
}
