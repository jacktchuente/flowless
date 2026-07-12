import { Pipe, PipeTransform } from "@angular/core";
@Pipe({ name: "flwTimeAgo", standalone: true, pure: false })
export class TimeAgoPipe implements PipeTransform {
  transform(value: string | Date | null | undefined): string {
    if (!value) return "—";
    const ms = Date.now() - new Date(value).getTime();
    if (!Number.isFinite(ms)) return "—";
    const mins = Math.max(0, Math.floor(ms / 60000));
    if (mins < 1) return "à l'instant";
    if (mins < 60) return `il y a ${mins} min`;
    const hours = Math.floor(mins / 60);
    if (hours < 24) return `il y a ${hours} h`;
    const days = Math.floor(hours / 24);
    return `il y a ${days} j`;
  }
}
