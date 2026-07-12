import { Injectable } from "@angular/core";
import { BehaviorSubject } from "rxjs";

export type ToastKind = "success" | "error" | "info";
export interface FlwToast {
  id: number;
  message: string;
  kind: ToastKind;
  action?: string;
  onAction?: () => void;
  duration: number;
}
@Injectable({ providedIn: "root" })
export class ToastService {
  private sequence = 0;
  private readonly state = new BehaviorSubject<FlwToast[]>([]);
  readonly toasts$ = this.state.asObservable();
  show(
    message: string,
    options: Partial<Omit<FlwToast, "id" | "message">> = {},
  ) {
    const toast: FlwToast = {
      id: ++this.sequence,
      message,
      kind: options.kind ?? "success",
      action: options.action,
      onAction: options.onAction,
      duration: options.duration ?? 4200,
    };
    this.state.next([...this.state.value, toast]);
    if (toast.duration > 0)
      setTimeout(() => this.dismiss(toast.id), toast.duration);
    return toast.id;
  }
  dismiss(id: number) {
    this.state.next(this.state.value.filter((item) => item.id !== id));
  }
  act(toast: FlwToast) {
    toast.onAction?.();
    this.dismiss(toast.id);
  }
}
