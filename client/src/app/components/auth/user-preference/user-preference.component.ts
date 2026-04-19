import {Component, Input, OnInit} from '@angular/core';
import {CommonModule} from '@angular/common';
import {FormGroup, FormsModule, ReactiveFormsModule} from "@angular/forms";
import {CRUDComponent} from "@kwyxyz/ngx-request";
import {UserPreference} from "@project-interfaces/user-preference";
import {UserPreferenceService} from "@project-services/user-preference.service";

import {FormlyFieldConfig, FormlyModule} from "@ngx-formly/core";
import {TranslateModule} from "@ngx-translate/core";

import {MatButton} from "@angular/material/button";
import {Languages} from "@project-utils/const";


@Component({
    selector: 'app-user-preference',
    standalone: true,
    imports: [
        CommonModule,
        FormsModule, ReactiveFormsModule, MatButton,
        FormlyModule,
        TranslateModule
    ],
    templateUrl: './user-preference.component.html',
    styleUrls: ['./user-preference.component.css']
})
export class UserPreferenceComponent extends CRUDComponent<UserPreference> implements OnInit {
    @Input() hideSubmitButton = false;


    updateFields: FormlyFieldConfig[] = [
        {
            fieldGroupClassName: "row",
            fieldGroup: [
                {
                    className: "col-md-6 col-12",
                    "key": "language",
                    "type": "select",
                    "props": {
                        "label": "Langue",
                        "required": false,
                        options: Languages
                    }
                },
                {
                    className: "col-md-6 col-12",
                    "key": "country",
                    "type": "input",
                    "props": {
                        "label": "Pays",
                        "required": false,
                    }
                },
            ]
        },
    ]


    constructor(
        protected userPreferenceService: UserPreferenceService,
    ) {
        super(userPreferenceService);


    }

    override ngOnInit() {
        super.ngOnInit()
        this.ngOnInitRetrieve()
        this.ngOnInitUpdate()
        this.setCurrentObjectWithId("me")
    }


    override getUpdateForm(): FormGroup {
        return this.formBuilder.group({})
    }


}
