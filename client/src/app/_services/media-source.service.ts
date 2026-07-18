import { Injectable } from "@angular/core";
import { HttpClient } from "@angular/common/http";
import { BaseApiService, ObjectApiService } from "@kwyxyz/ngx-request";
import { apiRoutes } from "../_utils/apiRoutes";
import {
  MediaSource,
  MediaSourcePayload,
  MediaSourceVerifyResponse,
} from "../_interfaces/media-source";
import { Observable, Subject } from "rxjs";

interface RequestResponseLike {
  isOk: boolean;
  body: unknown;
}

@Injectable({
  providedIn: "root",
})
export class MediaSourceApiService extends BaseApiService {
  override resourcePart = apiRoutes.mediaSource;

  constructor(http: HttpClient) {
    super(http);
  }

  verifyCredentials(
    payload: MediaSourcePayload,
  ): Observable<MediaSourceVerifyResponse> {
    return this.http.post<MediaSourceVerifyResponse>(
      `${this.getFullUrl()}verify/`,
      payload,
    );
  }

  syncCollections(id: string | number): Observable<null> {
    return this.http.post<null>(`${this.getFullUrl()}${id}/analyze/`, {});
  }

  setActive(id: string | number, isActive: boolean): Observable<MediaSource> {
    return this.http.post<MediaSource>(`${this.getFullUrl()}${id}/set-active/`, {
      is_active: isActive,
    });
  }
}

@Injectable({
  providedIn: "root",
})
export class MediaSourceService extends ObjectApiService {
  override data: { [indexer: string]: MediaSource } = {};
  override baseName = "mediaSource";
  override objectName = "MediaSource"; // do not edit
  // La page confirme déjà via FlwConfirm avant deleteObject
  override confirmedBeforeDelete = false;
  private lastQueryParams: Record<string, unknown> | null = null;

  constructor(protected override api: MediaSourceApiService) {
    super(api);
  }

  override listObject(
    queryParam: Record<string, unknown> | null = null,
    replace = false,
    url = undefined,
  ) {
    this.lastQueryParams = queryParam;
    return super.listObject(queryParam, replace, url);
  }

  override onCreateEvent(): void {
    this.refreshFromSocket();
  }

  override onUpdateEvent(): void {
    this.refreshFromSocket();
  }

  override onDestroyEvent(): void {
    this.refreshFromSocket();
  }

  verifyCredentials(payload: MediaSourcePayload): Subject<RequestResponseLike> {
    const subject = new Subject<RequestResponseLike>();
    this.api.verifyCredentials(payload).subscribe({
      next: (body) => subject.next({ isOk: true, body }),
      error: (body) => subject.next({ isOk: false, body }),
    });
    return subject;
  }

  syncCollections(id: string | number): Subject<RequestResponseLike> {
    const subject = new Subject<RequestResponseLike>();
    this.api.syncCollections(id).subscribe({
      next: (body) => subject.next({ isOk: true, body }),
      error: (body) => subject.next({ isOk: false, body }),
    });
    return subject;
  }

  setActive(id: string | number, isActive: boolean): Subject<RequestResponseLike> {
    const subject = new Subject<RequestResponseLike>();
    this.api.setActive(id, isActive).subscribe({
      next: (body) => subject.next({ isOk: true, body }),
      error: (body) => subject.next({ isOk: false, body }),
    });
    return subject;
  }

  private refreshFromSocket() {
    this.listObject(this.lastQueryParams, true);
  }
}
