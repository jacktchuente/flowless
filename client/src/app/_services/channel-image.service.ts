import { Injectable } from "@angular/core";
import { HttpClient } from "@angular/common/http";
import { BaseApiService } from "@kwyxyz/ngx-request";
import { Observable, Subject } from "rxjs";
import {
  ChannelImageRunPayload,
  ChannelImageSuggestionRun,
} from "@project-interfaces/channel-image";
import { TvChannel } from "@project-interfaces/tv-channel";
import { apiRoutes } from "../_utils/apiRoutes";

interface RequestResponseLike {
  isOk: boolean;
  body: unknown;
}

@Injectable({
  providedIn: "root",
})
export class ChannelImageApiService extends BaseApiService {
  override resourcePart = apiRoutes.channelImageRun;

  constructor(http: HttpClient) {
    super(http);
  }

  listRuns(channelId: string | number): Observable<ChannelImageSuggestionRun[]> {
    return this.http.get<ChannelImageSuggestionRun[]>(this.getFullUrl(), {
      params: { tv_channel: channelId },
    });
  }

  createRun(payload: ChannelImageRunPayload): Observable<null> {
    return this.http.post<null>(this.getFullUrl(), payload);
  }

  choose(runId: string | number, suggestionId: string | number): Observable<TvChannel> {
    return this.http.post<TvChannel>(`${this.getFullUrl()}${runId}/choose/`, {
      suggestion_id: suggestionId,
    });
  }

  deleteRun(runId: string | number): Observable<null> {
    return this.http.delete<null>(`${this.getFullUrl()}${runId}/`);
  }
}

@Injectable({
  providedIn: "root",
})
export class ChannelImageService {
  constructor(private api: ChannelImageApiService) {}

  private wrap(request: Observable<unknown>): Subject<RequestResponseLike> {
    const subject = new Subject<RequestResponseLike>();
    request.subscribe({
      next: (body) => subject.next({ isOk: true, body }),
      error: (body) => subject.next({ isOk: false, body }),
    });
    return subject;
  }

  listRuns(channelId: string | number) {
    return this.wrap(this.api.listRuns(channelId));
  }

  createRun(payload: ChannelImageRunPayload) {
    return this.wrap(this.api.createRun(payload));
  }

  choose(runId: string | number, suggestionId: string | number) {
    return this.wrap(this.api.choose(runId, suggestionId));
  }

  deleteRun(runId: string | number) {
    return this.wrap(this.api.deleteRun(runId));
  }
}
