import { Injectable } from "@angular/core";
import { HttpClient } from "@angular/common/http";
import { Observable } from "rxjs";
import { BaseApiService } from "@kwyxyz/ngx-request";
import { DashboardOverview } from "../_interfaces/dashboard";
import { apiRoutes } from "../_utils/apiRoutes";
@Injectable({ providedIn: "root" })
export class DashboardService extends BaseApiService {
  override resourcePart = apiRoutes.dashboard;
  constructor(http: HttpClient) {
    super(http);
  }
  overview(): Observable<DashboardOverview> {
    return this.http.get<DashboardOverview>(`${this.getFullUrl()}/`);
  }
}
