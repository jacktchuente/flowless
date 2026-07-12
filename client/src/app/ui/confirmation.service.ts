import { Injectable, Injector } from "@angular/core";
import { Observable, from, map, switchMap } from "rxjs";
import { TranslateService } from "@ngx-translate/core";

/**
 * Fourni à NgxRequestModule (PartialConfirmationService) : confirmation générique en flw-modal.
 * Les imports sont dynamiques pour garder CDK Dialog hors du bundle initial.
 */
@Injectable({ providedIn: "root" })
export class FlwConfirmationService {
  constructor(
    private injector: Injector,
    private translate: TranslateService,
  ) {}

  openConfirmationDialog(message: string | null = null): Observable<boolean> {
    return from(
      Promise.all([
        import("./dialog.service"),
        import("./confirm/flw-confirm.component"),
      ]),
    ).pipe(
      switchMap(
        ([dialogModule, confirmModule]) =>
          this.injector
            .get(dialogModule.FlwDialogService)
            .open(confirmModule.FlwConfirmComponent, {
              data: {
                title: this.translate.instant("COMMON.CONFIRM_TITLE"),
                message:
                  message ?? this.translate.instant("COMMON.CONFIRM_MESSAGE"),
                confirmLabel: this.translate.instant("COMMON.CONFIRM"),
              },
            }).closed,
      ),
      map((result) => result === true),
    );
  }
}
