import { Injectable } from "@angular/core";
import { HttpClient } from "@angular/common/http";
import { BaseApiService, ObjectApiService } from "@kwyxyz/ngx-request";
import { apiRoutes } from "../_utils/apiRoutes";
import {
  EditorialLineData,
  EditorialLinePayload,
  FormOptions,
  FormSuggestionRequest,
  FormSuggestionResponse,
  GridData,
  GridPayload,
  GridWarningsResponse,
  MarathonConfigData,
  PlayoutGenerationReport,
  RuleOptionSearchResponse,
  TvChannel,
} from "../_interfaces/tv-channel";
import { Observable, Subject } from "rxjs";
import { ChannelImageQueryPreview } from "@project-interfaces/channel-image";

interface RequestResponseLike {
  isOk: boolean;
  body: unknown;
}

export interface TvChannelBlueprintPayload {
  reboot?: boolean;
  grid_generation_mode: "full_llm" | "random" | "preset_and_llm";
  grid_only: boolean;
}

export interface TvPlayoutGenerationPayload {
  days: number;
  reset: boolean;
}

export interface TvChannelResetRulesPayload {
  types: Array<
    | "nature"
    | "kind"
    | "category"
    | "genre"
    | "tag"
    | "director"
    | "writer"
    | "creator"
    | "actor"
    | "studio"
    | "country"
    | "audio_language"
    | "subtitle_language"
  >;
  levels: Array<"allowed" | "forbidden">;
}

export interface TvChannelLogoPromptResponse {
  prompt: string;
}

export interface TvChannelNameSuggestionResponse {
  name: string;
}

@Injectable({
  providedIn: "root",
})
export class TvChannelApiService extends BaseApiService {
  override resourcePart = apiRoutes.tvChannel;

  constructor(http: HttpClient) {
    super(http);
  }

  generateBlueprint(
    id: string | number,
    payload: TvChannelBlueprintPayload,
  ): Observable<null> {
    return this.http.post<null>(
      `${this.getFullUrl()}${id}/generate-blueprint/`,
      payload,
    );
  }

  generatePlayout(
    id: string | number,
    payload: TvPlayoutGenerationPayload,
  ): Observable<unknown> {
    return this.http.post(
      `${this.getFullUrl()}${id}/generate-playout/`,
      payload,
    );
  }

  push(id: string | number): Observable<unknown> {
    return this.http.post(`${this.getFullUrl()}${id}/push/`, {});
  }

  resetRules(
    id: string | number,
    payload: TvChannelResetRulesPayload,
  ): Observable<null> {
    return this.http.post<null>(
      `${this.getFullUrl()}${id}/reset-rules/`,
      payload,
    );
  }

  exportLogoPrompt(
    id: string | number,
  ): Observable<TvChannelLogoPromptResponse> {
    return this.http.post<TvChannelLogoPromptResponse>(
      `${this.getFullUrl()}${id}/export-logo-prompt/`,
      {},
    );
  }

  suggestName(
    id: string | number,
  ): Observable<TvChannelNameSuggestionResponse> {
    return this.http.post<TvChannelNameSuggestionResponse>(
      `${this.getFullUrl()}${id}/suggest-name/`,
      {},
    );
  }

  uploadLogo(id: string | number, file: File): Observable<TvChannel> {
    const formData = new FormData();
    formData.append("logo", file);
    return this.http.post<TvChannel>(
      `${this.getFullUrl()}${id}/upload-logo/`,
      formData,
    );
  }

  getDetail(id: string | number): Observable<TvChannel> {
    return this.http.get<TvChannel>(`${this.getFullUrl()}${id}/`);
  }

  getGenerationReports(
    id: string | number,
  ): Observable<PlayoutGenerationReport[]> {
    return this.http.get<PlayoutGenerationReport[]>(
      `${this.getFullUrl()}${id}/generation-reports/`,
    );
  }

  generateLogo(
    id: string | number,
    backend: string | null,
  ): Observable<unknown> {
    return this.http.post(`${this.getFullUrl()}${id}/generate-logo/`, {
      backend,
    });
  }

  getFormOptions(): Observable<FormOptions> {
    return this.http.get<FormOptions>(`${this.getFullUrl()}form-options/`);
  }
  searchRuleOptions(
    query: string,
    limit = 20,
  ): Observable<RuleOptionSearchResponse> {
    return this.http.get<RuleOptionSearchResponse>(
      `${this.getFullUrl()}rule-option-search/`,
      { params: { q: query, limit } },
    );
  }
  getEditorialLine(id: string | number): Observable<EditorialLineData> {
    return this.http.get<EditorialLineData>(
      `${this.getFullUrl()}${id}/editorial-line/`,
    );
  }
  updateEditorialLine(
    id: string | number,
    payload: Partial<EditorialLinePayload>,
    partial = true,
  ): Observable<EditorialLineData> {
    return partial
      ? this.http.patch<EditorialLineData>(
          `${this.getFullUrl()}${id}/editorial-line/`,
          payload,
        )
      : this.http.put<EditorialLineData>(
          `${this.getFullUrl()}${id}/editorial-line/`,
          payload,
        );
  }
  updateGrid(id: string | number, payload: GridPayload): Observable<GridData> {
    return this.http.patch<GridData>(
      `${this.getFullUrl()}${id}/grid/`,
      payload,
    );
  }
  createGridVersion(id: string | number): Observable<GridData> {
    return this.http.post<GridData>(
      `${this.getFullUrl()}${id}/grid/new-version/`,
      {},
    );
  }
  getGridWarnings(id: string | number): Observable<GridWarningsResponse> {
    return this.http.get<GridWarningsResponse>(
      `${this.getFullUrl()}${id}/grid-warnings/`,
    );
  }
  getMarathonConfig(id: string | number): Observable<MarathonConfigData> {
    return this.http.get<MarathonConfigData>(
      `${this.getFullUrl()}${id}/marathon-config/`,
    );
  }
  getImageQueryPreview(id: string | number): Observable<ChannelImageQueryPreview> {
    return this.http.get<ChannelImageQueryPreview>(
      `${this.getFullUrl()}${id}/image-query-preview/`,
    );
  }
  updateMarathonConfig(
    id: string | number,
    payload: MarathonConfigData,
  ): Observable<MarathonConfigData> {
    return this.http.put<MarathonConfigData>(
      `${this.getFullUrl()}${id}/marathon-config/`,
      payload,
    );
  }
  suggestForm(
    id: string | number,
    payload: FormSuggestionRequest,
  ): Observable<FormSuggestionResponse> {
    return this.http.post<FormSuggestionResponse>(
      `${this.getFullUrl()}${id}/suggest-form/`,
      payload,
    );
  }
}

@Injectable({
  providedIn: "root",
})
export class TvChannelService extends ObjectApiService {
  override data: { [indexer: string]: TvChannel } = {};
  override baseName = "tvChannel";
  override objectName = "TvChannel";
  // La page confirme déjà via FlwConfirm avant deleteObject
  override confirmedBeforeDelete = false;
  private lastQueryParams: Record<string, unknown> | null = null;

  constructor(protected override api: TvChannelApiService) {
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

  generateBlueprint(
    id: string | number,
    payload: TvChannelBlueprintPayload,
  ): Subject<RequestResponseLike> {
    const subject = new Subject<RequestResponseLike>();
    this.api.generateBlueprint(id, payload).subscribe({
      next: (body) => subject.next({ isOk: true, body }),
      error: (body) => subject.next({ isOk: false, body }),
    });
    return subject;
  }

  generatePlayout(
    id: string | number,
    payload: TvPlayoutGenerationPayload,
  ): Subject<RequestResponseLike> {
    const subject = new Subject<RequestResponseLike>();
    this.api.generatePlayout(id, payload).subscribe({
      next: (body) => subject.next({ isOk: true, body }),
      error: (body) => subject.next({ isOk: false, body }),
    });
    return subject;
  }

  push(id: string | number): Subject<RequestResponseLike> {
    const subject = new Subject<RequestResponseLike>();
    this.api.push(id).subscribe({
      next: (body) => subject.next({ isOk: true, body }),
      error: (body) => subject.next({ isOk: false, body }),
    });
    return subject;
  }

  resetRules(
    id: string | number,
    payload: TvChannelResetRulesPayload,
  ): Subject<RequestResponseLike> {
    const subject = new Subject<RequestResponseLike>();
    this.api.resetRules(id, payload).subscribe({
      next: (body) => subject.next({ isOk: true, body }),
      error: (body) => subject.next({ isOk: false, body }),
    });
    return subject;
  }

  exportLogoPrompt(id: string | number): Subject<RequestResponseLike> {
    const subject = new Subject<RequestResponseLike>();
    this.api.exportLogoPrompt(id).subscribe({
      next: (body) => subject.next({ isOk: true, body }),
      error: (body) => subject.next({ isOk: false, body }),
    });
    return subject;
  }

  suggestName(id: string | number): Subject<RequestResponseLike> {
    const subject = new Subject<RequestResponseLike>();
    this.api.suggestName(id).subscribe({
      next: (body) => subject.next({ isOk: true, body }),
      error: (body) => subject.next({ isOk: false, body }),
    });
    return subject;
  }

  generateLogo(
    id: string | number,
    backend: string | null,
  ): Subject<RequestResponseLike> {
    const subject = new Subject<RequestResponseLike>();
    this.api.generateLogo(id, backend).subscribe({
      next: (body) => subject.next({ isOk: true, body }),
      error: (body) => subject.next({ isOk: false, body }),
    });
    return subject;
  }

  uploadLogo(id: string | number, file: File): Subject<RequestResponseLike> {
    const subject = new Subject<RequestResponseLike>();
    this.api.uploadLogo(id, file).subscribe({
      next: (body) => subject.next({ isOk: true, body }),
      error: (body) => subject.next({ isOk: false, body }),
    });
    return subject;
  }

  getDetail(id: string | number): Subject<RequestResponseLike> {
    const subject = new Subject<RequestResponseLike>();
    this.api.getDetail(id).subscribe({
      next: (body) => subject.next({ isOk: true, body }),
      error: (body) => subject.next({ isOk: false, body }),
    });
    return subject;
  }

  getGenerationReports(id: string | number) {
    return this.wrap(this.api.getGenerationReports(id));
  }

  private wrap(request: Observable<unknown>): Subject<RequestResponseLike> {
    const subject = new Subject<RequestResponseLike>();
    request.subscribe({
      next: (body) => subject.next({ isOk: true, body }),
      error: (body) => subject.next({ isOk: false, body }),
    });
    return subject;
  }
  getFormOptions() {
    return this.wrap(this.api.getFormOptions());
  }
  // Flux brut (pas de wrap isOk) : consomme directement par l'autocomplete.
  searchRuleOptions(query: string, limit = 20) {
    return this.api.searchRuleOptions(query, limit);
  }
  getEditorialLine(id: string | number) {
    return this.wrap(this.api.getEditorialLine(id));
  }
  updateEditorialLine(
    id: string | number,
    payload: Partial<EditorialLinePayload>,
    partial = true,
  ) {
    return this.wrap(this.api.updateEditorialLine(id, payload, partial));
  }
  updateGrid(id: string | number, payload: GridPayload) {
    return this.wrap(this.api.updateGrid(id, payload));
  }
  createGridVersion(id: string | number) {
    return this.wrap(this.api.createGridVersion(id));
  }
  getGridWarnings(id: string | number) {
    return this.wrap(this.api.getGridWarnings(id));
  }
  getMarathonConfig(id: string | number) {
    return this.wrap(this.api.getMarathonConfig(id));
  }
  getImageQueryPreview(id: string | number) {
    return this.wrap(this.api.getImageQueryPreview(id));
  }
  updateMarathonConfig(id: string | number, payload: MarathonConfigData) {
    return this.wrap(this.api.updateMarathonConfig(id, payload));
  }
  suggestForm(id: string | number, payload: FormSuggestionRequest) {
    return this.wrap(this.api.suggestForm(id, payload));
  }

  private refreshFromSocket() {
    this.listObject(this.lastQueryParams, true);
  }

  protected override getRequestWhenConstruct(): any {
    return false;
  }
}
