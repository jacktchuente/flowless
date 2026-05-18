import {Injectable} from '@angular/core';
import {HttpClient} from "@angular/common/http";
import {BaseApiService, ObjectApiService} from "@kwyxyz/ngx-request";
import {apiRoutes} from "../_utils/apiRoutes";
import {MediaCollection} from "../_interfaces/media-collection";
import {Observable, Subject} from "rxjs";

interface RequestResponseLike {
  isOk: boolean
  body: unknown
}

@Injectable({
  providedIn: 'root'
})
export class MediaCollectionApiService extends BaseApiService {
  override resourcePart = apiRoutes.mediaCollection

  constructor(http: HttpClient) {
    super(http);
  }

  analyze(id: string | number): Observable<null> {
    return this.http.post<null>(`${this.getFullUrl()}${id}/analyze/`, {});
  }
}

@Injectable({
  providedIn: 'root'
})
export class MediaCollectionService extends ObjectApiService {
  override data: { [indexer: string]: MediaCollection } = {}
  override baseName = 'mediaCollection'
  override objectName = 'MediaCollection'
  private lastQueryParams: Record<string, unknown> | null = null

  constructor(protected override api: MediaCollectionApiService) {
    super(api)
  }

  override listObject(queryParam: Record<string, unknown> | null = null, replace = false, url = undefined) {
    this.lastQueryParams = queryParam
    return super.listObject(queryParam, replace, url)
  }

  override onCreateEvent(): void {
    this.refreshFromSocket()
  }

  override onUpdateEvent(): void {
    this.refreshFromSocket()
  }

  override onDestroyEvent(): void {
    this.refreshFromSocket()
  }

  analyze(id: string | number): Subject<RequestResponseLike> {
    const subject = new Subject<RequestResponseLike>()
    this.api.analyze(id).subscribe({
      next: (body) => subject.next({isOk: true, body}),
      error: (body) => subject.next({isOk: false, body}),
    })
    return subject
  }

  private refreshFromSocket() {
    this.listObject(this.lastQueryParams, true)
  }
}
