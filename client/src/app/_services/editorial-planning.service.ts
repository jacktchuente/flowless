import {Injectable} from '@angular/core';
import {HttpClient} from "@angular/common/http";
import {BaseApiService} from "@kwyxyz/ngx-request";
import {Observable, Subject} from "rxjs";
import {EditorialChannelCandidate} from "@project-interfaces/editorial-planning";
import {TvChannel} from "@project-interfaces/tv-channel";
import {apiRoutes} from "../_utils/apiRoutes";

interface RequestResponseLike {
  isOk: boolean
  body: unknown
}

@Injectable({
  providedIn: 'root'
})
export class EditorialChannelCandidateApiService extends BaseApiService {
  override resourcePart = apiRoutes.editorialChannelCandidate

  constructor(http: HttpClient) {
    super(http);
  }

  listCandidates(queryParams: Record<string, string | number>): Observable<EditorialChannelCandidate[]> {
    return this.http.get<EditorialChannelCandidate[]>(this.getFullUrl(), {params: queryParams});
  }

  createFlexibleChannel(id: string | number, name?: string): Observable<TvChannel> {
    return this.http.post<TvChannel>(`${this.getFullUrl()}${id}/create-flexible-channel/`, {name: name || ""});
  }
}

@Injectable({
  providedIn: 'root'
})
export class EditorialPlanningService {
  constructor(private api: EditorialChannelCandidateApiService) {}

  listCandidates(queryParams: Record<string, string | number>): Subject<RequestResponseLike> {
    const subject = new Subject<RequestResponseLike>()
    this.api.listCandidates(queryParams).subscribe({
      next: (body) => subject.next({isOk: true, body}),
      error: (body) => subject.next({isOk: false, body}),
    })
    return subject
  }

  createFlexibleChannel(id: string | number, name?: string): Subject<RequestResponseLike> {
    const subject = new Subject<RequestResponseLike>()
    this.api.createFlexibleChannel(id, name).subscribe({
      next: (body) => subject.next({isOk: true, body}),
      error: (body) => subject.next({isOk: false, body}),
    })
    return subject
  }
}
