import {BaseApi} from "./interfaces/base-api";
import {HttpClient} from "@angular/common/http";
import {NgxRequestModule} from "./ngx-request.module";
import {BehaviorSubject, map, Observable, Subject} from "rxjs";
import {sortDataByFields} from "./utils/functions.utils";
import {RequestResponse} from "./interfaces/request-response";
import {INotificationService, PartialNotificationService} from "./interfaces/notification-service";
import {IConfirmationService, PartialConfirmationService} from "./interfaces/confirmation-service";
import {ILoadingService, PartialLoadingService} from "./interfaces/loading-service";
import {filter} from 'rxjs/operators';
import {WebsocketService, WsCRUDData} from "./ngx-websocket.service";

export abstract class BaseApiService implements BaseApi {
    public resourcePart = ''
    public customApiUrl: string | null = null
    public readonly defaultApiUrl: string

    protected constructor(protected http: HttpClient) {
        const injector = NgxRequestModule.InjectorInstance
        this.defaultApiUrl = injector.get('defaultApiUrl')

    }

    protected getFullUrl() {
        let apiUrl = this.customApiUrl ? this.customApiUrl : this.defaultApiUrl
        apiUrl = apiUrl.trim().replace(/\/$/g, "")
        return `${apiUrl}/${this.resourcePart}`.trim().replace(/\/$/g, "") + '/'
    }

    public getObject(id: string | null = null, queryParameter?: {}, url = undefined): Observable<any> {
        const req = url ? url : this.getFullUrl()
        if (id !== null) {
            return this.http.get<any>(req + id.toString() + '/', {params: queryParameter});
        }
        return this.http.get<any>(req, {params: queryParameter});
    }

    public patchObject(objectId: string, objectData: {}, url = undefined): Observable<any> {
        const req = url ? url : this.getFullUrl()

        return this.http.patch<any>(req + objectId + '/', objectData);
    }

    public deleteObject(objectId: string, url = undefined): Observable<any> {
        const req = url ? url : this.getFullUrl()

        return this.http.delete<any>(req + objectId);
    }

    public createObject(objectData: {}, url = undefined): Observable<any> {
        const req = url ? url : this.getFullUrl()

        return this.http.post<any>(req, objectData);
    }

}


export class ObjectApiService {
    public data: { [indexer: string]: {} } = {}
    nextPageUrl = new BehaviorSubject<string | null>(null)
    previousPageUrl = new BehaviorSubject<string | null>(null)
    count = 0
    currentPage = 0
    messageCategory: null | string = null
    protected paginate = false;
    protected resultKey = 'results'
    protected nextPageKey = 'next'
    protected previousPageKey = 'past'
    protected confirmedBeforeDelete = true

    protected successPostNotification: boolean = true
    protected successPatchNotification: boolean = true
    protected successDeleteNotification: boolean = true
    protected successGetNotification: boolean = false

    protected failPostNotification: boolean = true
    protected failPatchNotification: boolean = true
    protected failDeleteNotification: boolean = true
    protected failGetNotification: boolean = true

    protected allowLoadingPostList: boolean = true

    protected baseName: string = 'base-name';
    protected objectName: string = 'base-name';
    protected keyId = 'id';
    protected sortBy: string[] = ['id']

    protected notificationService: INotificationService
    protected confirmationService: IConfirmationService
    protected loadingService: ILoadingService

    protected requestWhenConstruct = this.getRequestWhenConstruct()
    protected objectBehaviorSubject = new BehaviorSubject<any>({});
    protected webSocketService: WebsocketService

    protected defaultIdOrder: string[] | number[] = []

    constructor(protected api: BaseApi) {
        const injector = NgxRequestModule.InjectorInstance
        this.notificationService = injector.get(PartialNotificationService)
        this.confirmationService = injector.get(PartialConfirmationService)
        this.webSocketService = injector.get(WebsocketService)
        this.loadingService = injector.get(PartialLoadingService)
        if (this.requestWhenConstruct) {
            this.listObject();
        }
        this.onWebsocketEvent()
    }

    protected onWebsocketEvent() {
        this.webSocketService.crudEvent
            .pipe(
                filter((x: any) => x.type.toLowerCase() === this.objectName.toLowerCase())
            )
            .subscribe(
                (x: any) => {
                    if (x.action === 'create') {
                        this.onCreateEvent(x)
                    } else if (x.action === 'update') {
                        this.onUpdateEvent(x)
                    } else if (x.action === 'destroy') {
                        this.onDestroyEvent(x)
                    }
                }
            )
    }

    protected onCreateEvent(event: WsCRUDData) {

    }

    protected onUpdateEvent(event: WsCRUDData) {

    }

    protected onDestroyEvent(event: WsCRUDData) {

    }

    public getObjectBehaviorSubject(): Observable<any> {
        let sortFields = this.sortBy ? this.sortBy : null
        return this.objectBehaviorSubject.pipe(map(
            res => {
                if (sortFields) {
                    const result: any[] = Array.from(Object.keys(res), k => res[k])
                    return result.sort(sortDataByFields(sortFields))
                }
                return this.setDefaultOrder(res)
            }
        ))
    }

    protected setDefaultOrder(data: {}): any[] {
        const orderedData: any[] = [];
        const remainingData: any[] = [];
        const dataMap = new Map(Array.from(Object.keys(data), key => [key, Reflect.get(data, key)]));
        this.defaultIdOrder.forEach((id: any) => {
            if (dataMap.has(id)) {
                orderedData.push(dataMap.get(id));
                dataMap.delete(id);
            }
        });
        dataMap.forEach((value) => remainingData.push(value));
        return [...orderedData, ...remainingData];
    }


    public listObject(queryParam: any = null, replace = false, url: string | undefined = undefined): Subject<RequestResponse> {
        const requestResponse = new Subject<RequestResponse>()
        if (this.allowLoadingPostList) {
            this.loadingService.loading(true)
        }
        this.api.getObject(null, queryParam, url)
            .subscribe(
                x => {
                    let data = x;
                    if (this.paginate) {
                        data = this.setPaginationData(x);
                    }
                    this.onSuccessListObject(data, replace, requestResponse);

                    if (this.allowLoadingPostList) {
                        this.loadingService.loading(false)
                    }

                },
                error => {
                    this.onFailListObject(error, requestResponse);

                    if (this.allowLoadingPostList) {
                        this.loadingService.loading(false)
                    }
                });
        return requestResponse
    }

    public nextListObject(queryParam: any = null, replace = false, url: string | undefined = undefined) {
        const requestUrl = url ?? this.nextPageUrl.getValue() ?? undefined
        return this.listObject(queryParam, replace, requestUrl)
    }

    public previousListObject(queryParam: any = null, replace = false, url: string | undefined = undefined) {
        const requestUrl = url ?? this.previousPageUrl.getValue() ?? undefined
        return this.listObject(queryParam, replace, requestUrl)
    }

    public getObject(objectId: any, queryParam: any = null): Subject<RequestResponse> {
        const response = new Subject<RequestResponse>()
        this.api.getObject(objectId, queryParam).subscribe(
            x => {
                this.onSuccessGetObject(objectId, x, response);
            },
            error => {
                this.onFailGetObject(error, response);
            }
        );
        return response
    }

    public createObject(objectData: Object, ...args: any): Subject<RequestResponse> {
        const subject = new Subject<RequestResponse>()
        this.api.createObject(objectData).subscribe(
            returnedObject => {
                this.onSuccessCreateObject(returnedObject, subject, ...args);
            },
            error => {
                this.onFailCreateObject(error, subject, ...args);
            }
        );
        return subject;
    }

    public deleteObject(objectId: string): Subject<RequestResponse> {
        const requestResponse = new Subject<RequestResponse>()

        const deleteObjectFn = () => {
            this.api.deleteObject(objectId).subscribe(
                returnedObject => {
                    this.onSuccessDeleteObject(returnedObject, objectId, requestResponse);
                },
                error => {
                    this.onFailDeleteObject(error, requestResponse);
                }
            );
        }
        if (this.confirmedBeforeDelete && this.confirmationService) {
            this.confirmationService.openConfirmationDialog().subscribe(
                (x: any) => {
                    if (x) {
                        deleteObjectFn()
                    }
                }
            )
        } else {
            deleteObjectFn()
        }
        return requestResponse
    }

    public patchObject(objectId: string, objectData: Object, ...args: unknown[]): Subject<RequestResponse> {
        const subject = new Subject<RequestResponse>()
        this.api.patchObject(objectId, objectData).subscribe(
            returnedObject => {
                this.onSuccessPatchObject(returnedObject, objectData, objectId, subject);
            },
            error => {
                this.onFailPatchObject(error, subject);
            }
        );
        return subject;
    }

    emptyData() {
        this.data = {}
    }

    public getItemById(objectId: any): any {
        return this.data[objectId];
    }

    protected onSuccessListObject(returnedObjects: any, replace = false,
                                  requestResponse: Subject<RequestResponse>, ...args: any): void {
        if (replace) {
            this.emptyData()
            this.defaultIdOrder = []
        }
        this.defaultIdOrder = [
            ...this.defaultIdOrder,
            ...Array.from(returnedObjects, (x: any) => Reflect.get(x, this.keyId))
        ]
        for (const returnedObject of returnedObjects) {
            this.addObjectToData(returnedObject)
        }
        this.syncData()
        if (requestResponse) {
            requestResponse.next({isOk: true, body: returnedObjects})
        }

    }

    protected onFailListObject(error: any, requestResponse: Subject<RequestResponse>): void {
        if (requestResponse) {
            requestResponse.next({isOk: false, body: error})
        }
    }

    protected onSuccessGetObject(objectId: number, returnedObject: object, requestResponse: Subject<RequestResponse>, ...args: any): void {
        this.addObjectToData(returnedObject)
        this.syncData()
        requestResponse.next({isOk: true, body: returnedObject})
        if (this.successGetNotification) {
            this.notificationService.notify(`${this.baseName}GetSuccessNotification`)
        }
    }

    protected onFailGetObject(error: any, requestResponse: Subject<RequestResponse>): void {
        requestResponse.next({isOk: false, body: error})
        if (this.successGetNotification) {
            this.notificationService.notify(`${this.baseName}GetFailNotification`)
        }
    }

    protected onSuccessCreateObject(returnedObject: any, requestResponse: Subject<RequestResponse>, ...args: any): void {
        this.addObjectToData(returnedObject);
        this.syncData()
        requestResponse.next({isOk: true, body: returnedObject})
        if (this.successPostNotification) {
            this.notificationService.notify(`${this.baseName}CreateSuccessNotification`)
        }
    }

    protected onFailCreateObject(error: any, requestResponse: Subject<RequestResponse>, ...args: any): void {
        requestResponse.next({isOk: false, body: error});
        if (this.failPostNotification) {
            this.notificationService.notify(`${this.baseName}CreateFailNotification`)
        }
    }

    protected onFailDeleteObject(error: any, requestResponse: Subject<RequestResponse>): void {
        requestResponse.next({isOk: false, body: error})
        if (this.failDeleteNotification) {
            this.notificationService.notify(`${this.baseName}DeleteFailNotification`)
        }
    }

    protected onSuccessDeleteObject(returnedObject: object | null, objectId: string, requestResponse: Subject<RequestResponse>): void {
        this.removeObjectFromData(objectId);
        this.syncData()
        if (this.successDeleteNotification) {
            this.notificationService.notify(`${this.baseName}DeleteSuccessNotification`)
        }
        requestResponse.next({isOk: true, body: returnedObject})
    }

    protected onSuccessPatchObject(returnedObject: object, objectData: object,
                                   objectId: string, requestResponse: Subject<RequestResponse>): void {
        this.addObjectToData(returnedObject, true)
        this.syncData()
        requestResponse.next({isOk: true, body: returnedObject})
        if (this.successPatchNotification) {
            this.notificationService.notify(`${this.baseName}SuccessPatchNotification`)
        }
    }

    protected onFailPatchObject(error: any, requestResponse: Subject<RequestResponse>): void {
        if (this.failPatchNotification) {
            this.notificationService.notify(`${this.baseName}FailPatchNotification`)
        }
        requestResponse.next({isOk: false, body: error})
    }

    protected getRequestWhenConstruct(): boolean {
        return true
    }

    public syncData() {
        this.objectBehaviorSubject.next(this.data)
    }

    protected removeObjectFromData(objectId: string): void {
        if (Object.keys(this.data).indexOf(objectId.toString()) > -1) {
            delete this.data[objectId]
        }
    }

    protected addObjectToData(returnedObject: any, partial: boolean = false) {
        const objectId = returnedObject[this.keyId]
        if (partial && Object.keys(this.data).indexOf(objectId) > -1) {
            for (const key of Object.keys(returnedObject)) {
                const dataItem: any = this.data[objectId]
                dataItem[key] = returnedObject[key]
            }
        }
        this.data[objectId] = returnedObject
    }

    protected setPaginationData(results: any): any {
        let data = null
        this.currentPage = results.current
        this.count = results.count
        if (Object.keys(results).indexOf(this.resultKey) > -1) {
            data = results[this.resultKey]
        }
        if (Object.keys(results).indexOf(this.nextPageKey) > -1) {
            this.nextPageUrl.next(results[this.nextPageKey]);
        }
        if (Object.keys(results).indexOf(this.previousPageKey) > -1) {
            this.previousPageUrl.next(results[this.previousPageKey]);
        }

        return data;
    }

}