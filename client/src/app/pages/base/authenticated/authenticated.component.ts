import {Component, OnInit} from '@angular/core';
import {BasePageDirective} from "@kwyxyz/ngx-common";
import {environment} from "../../../../environments/environment";
import {RouterOutlet} from "@angular/router";


@Component({
    selector: 'app-authenticated',
    templateUrl: './authenticated.component.html',
    standalone: true,
    imports: [
        RouterOutlet,
    ],

    styleUrls: ['./authenticated.component.css']
})
export class AuthenticatedComponent extends BasePageDirective implements OnInit {

    pageName: string | null = ""
    override title = "AuthenticatedTitle"
    override description = "AuthenticatedDescription"
    override keywords = "AuthenticatedKeywords"
    // replace-me 12345
    defaultLanguage = undefined

    appName = environment.appName


}

