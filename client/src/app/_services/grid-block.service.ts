import {Injectable} from '@angular/core';
import {HttpClient} from "@angular/common/http";
import {BaseApiService} from "@kwyxyz/ngx-request";
import {apiRoutes} from "../_utils/apiRoutes";
import {Observable, Subject} from "rxjs";

interface RequestResponseLike {
  isOk: boolean
  body: unknown
}

export interface GridBlockAvailableMediaCount {
  count: number
}

@Injectable({
  providedIn: 'root'
})
export class GridBlockApiService extends BaseApiService {
  override resourcePart = apiRoutes.gridBlock

  constructor(http: HttpClient) {
    super(http);
  }

  getAvailableMediaCount(id: string | number): Observable<GridBlockAvailableMediaCount> {
    return this.http.get<GridBlockAvailableMediaCount>(`${this.getFullUrl()}${id}/available-media-count/`)
  }
}

@Injectable({
  providedIn: 'root'
})
export class GridBlockService {
  constructor(private api: GridBlockApiService) {}

  getAvailableMediaCount(id: string | number): Subject<RequestResponseLike> {
    const subject = new Subject<RequestResponseLike>()
    this.api.getAvailableMediaCount(id).subscribe({
      next: (body) => subject.next({isOk: true, body}),
      error: (body) => subject.next({isOk: false, body}),
    })
    return subject
  }
}
