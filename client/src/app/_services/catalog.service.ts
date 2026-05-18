import {Injectable} from '@angular/core';
import {HttpClient} from "@angular/common/http";
import {BaseApiService, ObjectApiService} from "@kwyxyz/ngx-request";
import {apiRoutes} from "../_utils/apiRoutes";
import {Catalog} from "../_interfaces/catalog";
import {Observable, Subject} from "rxjs";

interface RequestResponseLike {
  isOk: boolean
  body: unknown
}

@Injectable({
  providedIn: 'root'
})
export class CatalogApiService extends BaseApiService {
  override resourcePart = apiRoutes.catalog

  constructor(http: HttpClient) {
    super(http);
  }

  generateChannels(id: string | number, reboot = false): Observable<null> {
    return this.http.post<null>(`${this.getFullUrl()}${id}/generate-channels/`, {reboot});
  }
}

@Injectable({
  providedIn: 'root'
})
export class CatalogService extends ObjectApiService {
  override data: { [indexer: string]: Catalog } = {}
  override baseName = 'catalog'
  override objectName = 'Catalog'
  private lastQueryParams: Record<string, unknown> | null = null

  constructor(protected override api: CatalogApiService) {
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

  generateChannels(id: string | number, reboot = false): Subject<RequestResponseLike> {
    const subject = new Subject<RequestResponseLike>()
    this.api.generateChannels(id, reboot).subscribe({
      next: (body) => subject.next({isOk: true, body}),
      error: (body) => subject.next({isOk: false, body}),
    })
    return subject
  }

  private refreshFromSocket() {
    this.listObject(this.lastQueryParams, true)
  }
}
