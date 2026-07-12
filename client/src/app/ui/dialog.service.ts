import { Injectable, Type } from "@angular/core";
import { Dialog, DialogConfig, DialogRef } from "@angular/cdk/dialog";

@Injectable({ providedIn: "root" })
export class FlwDialogService {
  constructor(private readonly dialog: Dialog) {}
  open<R = any, D = any, C = any>(
    component: Type<C>,
    config: DialogConfig<D, DialogRef<R, C>> = {},
  ): DialogRef<R, C> {
    return this.dialog.open<R, D, C>(component, {
      ...config,
      hasBackdrop: true,
      backdropClass: "flw-dialog-backdrop",
      panelClass: "flw-dialog-pane",
      disableClose: false,
    });
  }
  closeAll() {
    this.dialog.closeAll();
  }
}
