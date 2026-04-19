import {Injectable} from '@angular/core';
import {HttpClient} from "@angular/common/http";
import {BaseApiService, ObjectApiService} from "@kwyxyz/ngx-request";
import {apiRoutes} from "../_utils/apiRoutes";
import {UserPreference} from "../_interfaces/user-preference";


@Injectable({
    providedIn: 'root'
})
export class UserPreferenceApiService extends BaseApiService {
    override resourcePart = apiRoutes.userPreference

    constructor(http: HttpClient) {
        super(http);
    }

}

@Injectable({
    providedIn: 'root'
})
export class UserPreferenceService extends ObjectApiService {
    override data: { [indexer: string]: UserPreference } = {}
    override baseName = 'userPreference'
    override objectName = 'UserPreference' // do not edit

    constructor(protected override api: UserPreferenceApiService) {
        super(api)
    }

    protected override getRequestWhenConstruct(): boolean {
        return false
    }
}
