import {Injectable} from '@angular/core';
import {HttpClient} from "@angular/common/http";
import {BaseApiService} from "@kwyxyz/ngx-request";
import {apiRoutes} from "../_utils/apiRoutes";
import {Observable, Subject} from "rxjs";
import {MediaContainerDetail, MediaContainerListItem, PaginatedResponse} from "@project-interfaces/media-container";

interface RequestResponseLike {
  isOk: boolean
  body: unknown
}

@Injectable({
  providedIn: 'root'
})
export class MediaContainerApiService extends BaseApiService {
  override resourcePart = apiRoutes.mediaContainer

  constructor(http: HttpClient) {
    super(http);
  }

  listPage(params: Record<string, string | number>): Observable<PaginatedResponse<MediaContainerListItem>> {
    return this.http.get<PaginatedResponse<MediaContainerListItem>>(this.getFullUrl(), {params})
  }

  getDetail(id: string | number): Observable<MediaContainerDetail> {
    return this.http.get<MediaContainerDetail>(`${this.getFullUrl()}${id}/`)
  }

  analyze(id: string | number): Observable<null> {
    return this.http.post<null>(`${this.getFullUrl()}${id}/analyse/`, {})
  }

  analyzeAll(): Observable<null> {
    return this.http.post<null>(`${this.getFullUrl()}analyse-all/`, {})
  }
}

@Injectable({
  providedIn: 'root'
})
export class MediaContainerService {
  constructor(private api: MediaContainerApiService) {}

  listPage(params: Record<string, string | number>): Subject<RequestResponseLike> {
    const subject = new Subject<RequestResponseLike>()
    this.api.listPage(params).subscribe({
      next: (body) => subject.next({isOk: true, body}),
      error: (body) => subject.next({isOk: false, body}),
    })
    return subject
  }

  getDetail(id: string | number): Subject<RequestResponseLike> {
    const subject = new Subject<RequestResponseLike>()
    this.api.getDetail(id).subscribe({
      next: (body) => subject.next({isOk: true, body}),
      error: (body) => subject.next({isOk: false, body}),
    })
    return subject
  }

  analyze(id: string | number): Subject<RequestResponseLike> {
    const subject = new Subject<RequestResponseLike>()
    this.api.analyze(id).subscribe({
      next: (body) => subject.next({isOk: true, body}),
      error: (body) => subject.next({isOk: false, body}),
    })
    return subject
  }

  analyzeAll(): Subject<RequestResponseLike> {
    const subject = new Subject<RequestResponseLike>()
    this.api.analyzeAll().subscribe({
      next: (body) => subject.next({isOk: true, body}),
      error: (body) => subject.next({isOk: false, body}),
    })
    return subject
  }
}
