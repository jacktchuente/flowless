import {Injectable} from '@angular/core';
import {MatSnackBar} from "@angular/material/snack-bar";
import {TranslateService} from "@ngx-translate/core";

@Injectable({
  providedIn: 'root'
})
export class NotificationService {

  constructor(private matSnackBar: MatSnackBar, private translateService: TranslateService) {
  }

  notify(message: string, duration = 10 * 10 ** 3) {
    this.translateService.get(message).subscribe(
      x => {
        if (x) {
          this.matSnackBar.open(x, 'Ok', {duration})
        }
      }
    )
  }
}
