export class DurationHandler {

  durationMulti = {
    second: 1000,
    day: 1000 * 3600 * 24
  }

  constructor(public durationLabel: string,
              public durationUnit: "second" | "day" = "second",
              public fieldAreDateTimeLocal = true) {
  }


  updateEndedAt(field: any) {
    const form = field.form;
    const duration = form.get(this.durationLabel).value;
    const startedAt = new Date(form.get('started_at').value);
    if (duration != null && startedAt) {
      const endedAt = new Date(startedAt.getTime() + duration * (this.durationMulti[this.durationUnit] ?? 1));
      const endedAtString = this.formatDate(endedAt, this.fieldAreDateTimeLocal)
      form.get('ended_at').setValue(endedAtString, {emitEvent: false});
    }
  }

  private formatDate(date: Date, isDateTimeLocal = true): string {

    if (isDateTimeLocal) {
      return date.getFullYear() +
        '-' + String(date.getMonth() + 1).padStart(2, '0') +
        '-' + String(date.getDate()).padStart(2, '0') +
        'T' + String(date.getHours()).padStart(2, '0') +
        ':' + String(date.getMinutes()).padStart(2, '0') +
        ':' + String(date.getSeconds()).padStart(2, '0')
    } else {
      return date.getFullYear() +
        '-' + String(date.getMonth() + 1).padStart(2, '0') +
        '-' + String(date.getDate()).padStart(2, '0')
    }
  }

  updateDuration(field: any) {
    const form = field.form;
    if (!form) {
      return
    }
    const startedAt = new Date(form.get('started_at')?.value);
    const endedAt = new Date(form.get('ended_at')?.value);
    if (startedAt && endedAt) {
      const duration = (endedAt.getTime() - startedAt.getTime()) / (this.durationMulti[this.durationUnit] ?? 1);
      form.get(this.durationLabel)?.setValue(duration, {emitEvent: false});
    }
  }
}
