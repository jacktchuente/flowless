import { Injectable } from "@angular/core";
import { BehaviorSubject } from "rxjs";

/** Fourni à NgxRequestModule (PartialLoadingService) : compte les requêtes en cours. */
@Injectable({ providedIn: "root" })
export class FlwLoadingService {
  private count = 0;
  private readonly state = new BehaviorSubject<boolean>(false);
  readonly loading$ = this.state.asObservable();

  loading(state: boolean) {
    this.count = Math.max(0, this.count + (state ? 1 : -1));
    this.state.next(this.count > 0);
  }
}
