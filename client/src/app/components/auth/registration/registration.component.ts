import {Component} from '@angular/core';
import {CommonModule} from '@angular/common';
import {ActivatedRoute, RouterLink} from "@angular/router";
import {LoginService, RegistrationDirective, RegistrationService} from "@kwyxyz/ngx-auth";
import {FormlyFieldConfig, FormlyModule} from "@ngx-formly/core";
import {FormBuilder, ReactiveFormsModule} from "@angular/forms";
import {TranslateModule, TranslateService} from "@ngx-translate/core";
import {BoxContainer3Component} from "@project-templates/box-container3/box-container3.component";
import {MatButton} from "@angular/material/button";
import {MatError} from "@angular/material/form-field";


@Component({
    selector: 'app-registration',
    standalone: true,
    imports: [CommonModule, BoxContainer3Component, FormlyModule, MatButton,
        MatError, ReactiveFormsModule, RouterLink, TranslateModule],
    templateUrl: './registration.component.html',
    styleUrls: ['./registration.component.css']
})
export class RegistrationComponent extends RegistrationDirective {
    override formLevelErrorMessages = ["Un objet utilisateur avec ce champ adresse électronique existe déjà."];

    fields: FormlyFieldConfig[] = [
        {
            key: 'email',
            type: 'input',
            props: {
                type: 'email',
                label: this.translateService.instant('REGISTRATION_FORM.EMAIL.LABEL'),
                placeholder: this.translateService.instant('REGISTRATION_FORM.EMAIL.PLACEHOLDER'),
                required: true,
                appearance: 'outline',
            },
        },
        {
            fieldGroupClassName: "row",
            fieldGroup: [
                {
                    key: 'first_name',
                    type: 'input',
                    className: "col-6",
                    props: {
                        label: this.translateService.instant('REGISTRATION_FORM.FIRST_NAME.LABEL'),
                        placeholder: this.translateService.instant('REGISTRATION_FORM.FIRST_NAME.PLACEHOLDER'),
                        required: true,
                    },
                },
                {
                    key: 'last_name',
                    type: 'input',
                    className: "col-6",
                    props: {
                        label: this.translateService.instant('REGISTRATION_FORM.LAST_NAME.LABEL'),
                        placeholder: this.translateService.instant('REGISTRATION_FORM.LAST_NAME.PLACEHOLDER'),
                        required: true,
                    },
                },
            ]
        },
        {
            validators: {
                validation: [
                    {name: 'fieldMatch', options: {errorPath: 'password2', field1: 'password', field2: 'password2'}},
                ],
            },
            fieldGroup: [
                {
                    key: 'password',
                    type: 'input',
                    props: {
                        type: 'password',
                        label: this.translateService.instant('REGISTRATION_FORM.PASSWORD.LABEL'),
                        placeholder: this.translateService.instant('REGISTRATION_FORM.PASSWORD.PLACEHOLDER'),
                        required: true,
                    },
                },
                {
                    key: 'password2',
                    type: 'input',
                    props: {
                        type: 'password',
                        label: this.translateService.instant('REGISTRATION_FORM.PASSWORD2.LABEL'),
                        placeholder: this.translateService.instant('REGISTRATION_FORM.PASSWORD2.PLACEHOLDER'),
                        required: true,
                    },
                },
            ]
        },
    ];

    constructor(protected override loginService: LoginService,
                protected override route: ActivatedRoute,
                protected override registrationService: RegistrationService,
                protected override formBuilder: FormBuilder,
                private translateService: TranslateService) {
        super(loginService, route, registrationService, formBuilder);
    }

}

