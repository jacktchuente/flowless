import {NgModule} from '@angular/core';
import {CommonModule} from '@angular/common';
import {FormlyPresetModule} from "@ngx-formly/core/preset";
import {FORMLY_CONFIG, FormlyModule} from "@ngx-formly/core";
import {Select2Input} from "@project-templates/select2/select2-input.component";
import {RepeatTypeComponent} from "@project-templates/repeat-type/repeat-type.component";
import {FormlyFieldStepperComponent} from "@project-templates/formly-field-stepper/formly-field-stepper.component";
import {FormlyBootstrapModule} from "@ngx-formly/bootstrap";
import {TranslateService} from "@ngx-translate/core";
import {registerTranslateExtension} from "./translate.extension";
import {ButtonInput1Component} from "@project-templates/button-input1/button-input1.component";
import {AbstractControl} from "@angular/forms";

export function startedAtBeforeEndAt(control: AbstractControl, options: {}) {
    // @ts-ignore
    const realOptions = options.validators.validation.find(x => x.name === "startedAtBeforeEndAt").options
    const field1 = Reflect.get(realOptions, "field1")
    const field2 = Reflect.get(realOptions, "field2")

    const startedAt = control.get(field1)?.value;
    const endedAt = control.get(field2)?.value;
    if (startedAt && endedAt) {
        const start = new Date(startedAt);
        const end = new Date(endedAt);
        if (start >= end) {
            return {startedAtBeforeEndAt: {message: "Dates incohérentes"}};
        }
    }

    return null;
}

export function fieldsAreIdentical(group: AbstractControl, options: {}) {
    // @ts-ignore
    const realOptions = options.validators.validation.find(x => x.name === "fieldMatch").options
    const field1 = Reflect.get(realOptions, "field1")
    const field2 = Reflect.get(realOptions, "field2")
    const password = group.get(field1)
    const password2 = group.get(field2)
    const pass = password ? password.value : null;
    const confirmPass = password2 ? password2.value : null;
    if (pass === confirmPass) {
        return null
    }
    return {fieldMatch: {message: 'Les mots de passe ne correspondent pas.'}};
}

function formatDate(date: Date): string {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    const hours = String(date.getHours()).padStart(2, '0');
    const minutes = String(date.getMinutes()).padStart(2, '0');
    const seconds = String(date.getSeconds()).padStart(2, '0');
    return `${year}-${month}-${day}T${hours}:${minutes}:${seconds}`;
}

@NgModule({
    declarations: [],
    imports: [
        CommonModule,
        FormlyPresetModule,
        FormlyModule.forRoot({
            validators: [
                {
                    name: 'fieldMatch',
                    validation: fieldsAreIdentical
                },
                {
                    name: 'startedAtBeforeEndAt',
                    validation: startedAtBeforeEndAt
                },

            ],
            types: [
                {name: 'select', component: Select2Input},
                {name: 'repeat', component: RepeatTypeComponent},
                {name: 'stepper', component: FormlyFieldStepperComponent, wrappers: []},
                {name: 'button', component: ButtonInput1Component},
            ],
            presets: [
                {
                    name: 'datetime',
                    config: {
                        className: "col-6",
                        key: 'recorded_at',
                        type: 'input',
                        defaultValue: formatDate(new Date()),
                        props: {
                            type: "datetime-local",
                            label: 'Enregistré à',
                        },
                    },
                },
                {
                    name: 'date',
                    config: {
                        key: 'recorded_at',
                        type: 'input',
                        className: "col-6",
                        props: {
                            type: "date",
                        },
                    },
                },

                {
                    name: 'recorded_at',
                    config: {
                        key: 'recorded_at',
                        type: 'input',
                        defaultValue: formatDate(new Date()),
                        props: {
                            type: "datetime-local",
                            label: 'Enregistré à',
                            description: "Select the record date"
                        },
                    },
                },
                {
                    name: "checkbox",
                    config: {}
                }
            ],
        }),
        FormlyBootstrapModule,
    ],
    providers: [
        {provide: FORMLY_CONFIG, multi: true, useFactory: registerTranslateExtension, deps: [TranslateService]},
    ],
})
export class CustomFormlyModule {
}
