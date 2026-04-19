import { Pipe, PipeTransform } from '@angular/core';

@Pipe({
  name: 'toDate',
  standalone: true
})
export class ToDatePipe implements PipeTransform {

  transform(value: string): any {
    return new Date(value);
  }

}
