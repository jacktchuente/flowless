import { Injectable } from "@angular/core";
import { HttpClient } from "@angular/common/http";
import { BaseApiService } from "@kwyxyz/ngx-request";
import { apiRoutes } from "../_utils/apiRoutes";
import { Observable, Subject } from "rxjs";
import { GridBlock, GridBlockPayload } from "../_interfaces/tv-channel";

interface RequestResponseLike {
  isOk: boolean;
  body: unknown;
}

export interface GridBlockAvailableMediaCount {
  count: number;
}

@Injectable({
  providedIn: "root",
})
export class GridBlockApiService extends BaseApiService {
  override resourcePart = apiRoutes.gridBlock;

  constructor(http: HttpClient) {
    super(http);
  }

  getAvailableMediaCount(
    id: string | number,
    payload?: Partial<GridBlockPayload>,
  ): Observable<GridBlockAvailableMediaCount> {
    const url = `${this.getFullUrl()}${id}/available-media-count/`;
    return payload
      ? this.http.post<GridBlockAvailableMediaCount>(url, payload)
      : this.http.get<GridBlockAvailableMediaCount>(url);
  }
  create(payload: GridBlockPayload): Observable<GridBlock> {
    return this.http.post<GridBlock>(this.getFullUrl(), payload);
  }
  update(
    id: string | number,
    payload: Partial<GridBlockPayload>,
  ): Observable<GridBlock> {
    return this.http.patch<GridBlock>(`${this.getFullUrl()}${id}/`, payload);
  }
  delete(id: string | number): Observable<void> {
    return this.http.delete<void>(`${this.getFullUrl()}${id}/`);
  }
}

@Injectable({
  providedIn: "root",
})
export class GridBlockService {
  constructor(private api: GridBlockApiService) {}

  getAvailableMediaCount(
    id: string | number,
    payload?: Partial<GridBlockPayload>,
  ): Subject<RequestResponseLike> {
    const subject = new Subject<RequestResponseLike>();
    this.api.getAvailableMediaCount(id, payload).subscribe({
      next: (body) => subject.next({ isOk: true, body }),
      error: (body) => subject.next({ isOk: false, body }),
    });
    return subject;
  }

  private wrap(request: Observable<unknown>): Subject<RequestResponseLike> {
    const subject = new Subject<RequestResponseLike>();
    request.subscribe({
      next: (body) => subject.next({ isOk: true, body }),
      error: (body) => subject.next({ isOk: false, body }),
    });
    return subject;
  }
  create(payload: GridBlockPayload) {
    return this.wrap(this.api.create(payload));
  }
  update(id: string | number, payload: Partial<GridBlockPayload>) {
    return this.wrap(this.api.update(id, payload));
  }
  delete(id: string | number) {
    return this.wrap(this.api.delete(id));
  }
}
