import {Pipe, PipeTransform} from '@angular/core';

@Pipe({
  name: 'duration',
  standalone: true
})
export class DurationPipe implements PipeTransform {

  transform(value: number, ...args: unknown[]): { value: number, unit: string } {
    const secondsInMinute = 60;
    const secondsInHour = 3600;
    const secondsInDay = 86400;
    if (value < secondsInMinute) {
      return {value, unit: 'second'};
    } else if (value < secondsInHour) {
      return {value: value / secondsInMinute, unit: 'mn'};
    } else if (value < secondsInDay) {
      return {value: value / secondsInHour, unit: 'h'};
    } else {
      return {value: value / secondsInDay, unit: 'j'};
    }
  }
}
