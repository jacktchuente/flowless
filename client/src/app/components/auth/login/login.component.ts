import {Component} from '@angular/core';
import {CommonModule} from '@angular/common';
import {ActivatedRoute, RouterLink} from "@angular/router";
import {NgxCommonModule} from "@kwyxyz/ngx-common";
import {BoxContainer3Component} from "../../../templates/box-container3/box-container3.component";
import {MatError} from "@angular/material/form-field";
import {MatButton} from "@angular/material/button";
import {TranslateModule, TranslateService} from "@ngx-translate/core";
import {LoginDirective, LoginService, OauthProvider} from "@kwyxyz/ngx-auth";
import {FormBuilder, ReactiveFormsModule} from "@angular/forms";
import {FormlyFieldConfig, FormlyModule} from "@ngx-formly/core";
import {MtxAlert} from "@ng-matero/extensions/alert";
import {environment} from "../../../../environments/environment";
import {HttpErrorResponse} from "@angular/common/http";


@Component({
    selector: 'app-login',
    standalone: true,
    imports: [CommonModule, BoxContainer3Component,
        MatButton, TranslateModule, ReactiveFormsModule, NgxCommonModule, RouterLink, MatError, FormlyModule, MtxAlert],
    templateUrl: './login.component.html',
    styleUrls: ['./login.component.css']
})
export class LoginComponent extends LoginDirective {


    oauthProviders: OauthProvider[] = [
        OauthProvider.discord,
        OauthProvider.google,
        OauthProvider.facebook,
        OauthProvider.microsoft,
        OauthProvider.twitter,
        OauthProvider.linkedin
    ]

    formLevelErrors: string[] = []
    private formLevelErrorMessages = ["username_password_mismatch"];
    fields: FormlyFieldConfig[] = [
        {
            key: 'email',
            type: 'input',
            props: {
                type: 'email',
                label: this.translateService.instant('Email'),
                placeholder: 'name@company.com',
                required: true,
            },
        },
        {
            key: 'password',
            type: 'input',
            props: {
                type: 'password',
                label: this.translateService.instant('Password'),
                placeholder: '••••••••',
                appearance: 'outline',
            },
        },
        {
            key: 'remember',
            type: 'checkbox',
            props: {
                label: this.translateService.instant('Se rappeler de moi'),
            },
        },
    ];
    showAlert = environment.mode === "demo";
    demoUserName = "demo@demo.demo";
    demoPassword = "demo"

    constructor(
        protected override loginService: LoginService,
        protected override route: ActivatedRoute,
        protected override formBuilder: FormBuilder,
        private translateService: TranslateService) {
        super(loginService, route, formBuilder);
    }

    override ngOnInit() {
        super.ngOnInit();
        this.sendingObservable.subscribe(
            x => {
                if (x) {
                    this.resetOnSending()
                }
            }
        )
        this.errorsObservable.subscribe(
            // @ts-ignore
            (errors: HttpErrorResponse) => {
                const err = errors.error
                const detail = err.detail
                if (this.formLevelErrorMessages.indexOf(detail) > -1) {
                    this.formLevelErrors.push(detail)
                }
            }
        )
    }

    resetOnSending() {
        this.formLevelErrors = []
    }
}

