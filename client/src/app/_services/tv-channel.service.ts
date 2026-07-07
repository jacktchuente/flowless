import {Injectable} from '@angular/core';
import {HttpClient} from "@angular/common/http";
import {BaseApiService, ObjectApiService} from "@kwyxyz/ngx-request";
import {apiRoutes} from "../_utils/apiRoutes";
import {PlayoutGenerationReport, TvChannel} from "../_interfaces/tv-channel";
import {Observable, Subject} from "rxjs";

interface RequestResponseLike {
    isOk: boolean
    body: unknown
}

export interface TvChannelBlueprintPayload {
    reboot?: boolean
    grid_generation_mode: 'full_llm' | 'random' | 'preset_and_llm'
    grid_only: boolean
}

export interface TvPlayoutGenerationPayload {
    days: number
    reset: boolean
}

export interface TvChannelResetRulesPayload {
    types: Array<'nature' | 'kind' | 'category'>
    levels: Array<'allowed' | 'forbidden'>
}

export interface TvChannelLogoPromptResponse {
    prompt: string
}

export interface TvChannelNameSuggestionResponse {
    name: string
}

@Injectable({
    providedIn: 'root'
})
export class TvChannelApiService extends BaseApiService {
    override resourcePart = apiRoutes.tvChannel

    constructor(http: HttpClient) {
        super(http);
    }

    generateBlueprint(id: string | number, payload: TvChannelBlueprintPayload): Observable<null> {
        return this.http.post<null>(`${this.getFullUrl()}${id}/generate-blueprint/`, payload);
    }

    generatePlayout(id: string | number, payload: TvPlayoutGenerationPayload): Observable<unknown> {
        return this.http.post(`${this.getFullUrl()}${id}/generate-playout/`, payload);
    }

    push(id: string | number): Observable<unknown> {
        return this.http.post(`${this.getFullUrl()}${id}/push/`, {});
    }

    resetRules(id: string | number, payload: TvChannelResetRulesPayload): Observable<null> {
        return this.http.post<null>(`${this.getFullUrl()}${id}/reset-rules/`, payload);
    }

    exportLogoPrompt(id: string | number): Observable<TvChannelLogoPromptResponse> {
        return this.http.post<TvChannelLogoPromptResponse>(`${this.getFullUrl()}${id}/export-logo-prompt/`, {});
    }

    suggestName(id: string | number): Observable<TvChannelNameSuggestionResponse> {
        return this.http.post<TvChannelNameSuggestionResponse>(`${this.getFullUrl()}${id}/suggest-name/`, {});
    }

    uploadLogo(id: string | number, file: File): Observable<TvChannel> {
        const formData = new FormData()
        formData.append('logo', file)
        return this.http.post<TvChannel>(`${this.getFullUrl()}${id}/upload-logo/`, formData);
    }

    getDetail(id: string | number): Observable<TvChannel> {
        return this.http.get<TvChannel>(`${this.getFullUrl()}${id}/`);
    }

    getGenerationReports(id: string | number): Observable<PlayoutGenerationReport[]> {
        return this.http.get<PlayoutGenerationReport[]>(`${this.getFullUrl()}${id}/generation-reports/`);
    }

    generateLogo(id: string | number, backend: string | null): Observable<unknown> {
        return this.http.post(`${this.getFullUrl()}${id}/generate-logo/`, {backend});
    }
}

@Injectable({
    providedIn: 'root'
})
export class TvChannelService extends ObjectApiService {
    override data: { [indexer: string]: TvChannel } = {}
    override baseName = 'tvChannel'
    override objectName = 'TvChannel'
    private lastQueryParams: Record<string, unknown> | null = null

    constructor(protected override api: TvChannelApiService) {
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

    generateBlueprint(id: string | number, payload: TvChannelBlueprintPayload): Subject<RequestResponseLike> {
        const subject = new Subject<RequestResponseLike>()
        this.api.generateBlueprint(id, payload).subscribe({
            next: (body) => subject.next({isOk: true, body}),
            error: (body) => subject.next({isOk: false, body}),
        })
        return subject
    }

    generatePlayout(id: string | number, payload: TvPlayoutGenerationPayload): Subject<RequestResponseLike> {
        const subject = new Subject<RequestResponseLike>()
        this.api.generatePlayout(id, payload).subscribe({
            next: (body) => subject.next({isOk: true, body}),
            error: (body) => subject.next({isOk: false, body}),
        })
        return subject
    }

    push(id: string | number): Subject<RequestResponseLike> {
        const subject = new Subject<RequestResponseLike>()
        this.api.push(id).subscribe({
            next: (body) => subject.next({isOk: true, body}),
            error: (body) => subject.next({isOk: false, body}),
        })
        return subject
    }

    resetRules(id: string | number, payload: TvChannelResetRulesPayload): Subject<RequestResponseLike> {
        const subject = new Subject<RequestResponseLike>()
        this.api.resetRules(id, payload).subscribe({
            next: (body) => subject.next({isOk: true, body}),
            error: (body) => subject.next({isOk: false, body}),
        })
        return subject
    }

    exportLogoPrompt(id: string | number): Subject<RequestResponseLike> {
        const subject = new Subject<RequestResponseLike>()
        this.api.exportLogoPrompt(id).subscribe({
            next: (body) => subject.next({isOk: true, body}),
            error: (body) => subject.next({isOk: false, body}),
        })
        return subject
    }

    suggestName(id: string | number): Subject<RequestResponseLike> {
        const subject = new Subject<RequestResponseLike>()
        this.api.suggestName(id).subscribe({
            next: (body) => subject.next({isOk: true, body}),
            error: (body) => subject.next({isOk: false, body}),
        })
        return subject
    }

    generateLogo(id: string | number, backend: string | null): Subject<RequestResponseLike> {
        const subject = new Subject<RequestResponseLike>()
        this.api.generateLogo(id, backend).subscribe({
            next: (body) => subject.next({isOk: true, body}),
            error: (body) => subject.next({isOk: false, body}),
        })
        return subject
    }

    uploadLogo(id: string | number, file: File): Subject<RequestResponseLike> {
        const subject = new Subject<RequestResponseLike>()
        this.api.uploadLogo(id, file).subscribe({
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

    private refreshFromSocket() {
        this.listObject(this.lastQueryParams, true)
    }

    protected override getRequestWhenConstruct(): any {
        return false
    }
}
