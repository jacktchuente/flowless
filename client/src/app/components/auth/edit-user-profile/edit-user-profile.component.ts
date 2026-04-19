import {Component} from '@angular/core';
import {CommonModule} from '@angular/common';
import {EditUserProfileDirective, UserService} from "@kwyxyz/ngx-auth";
import {NgxCommonModule} from "@kwyxyz/ngx-common";
import {FormBuilder, ReactiveFormsModule} from "@angular/forms";
import {TranslateModule, TranslateService} from "@ngx-translate/core";
import {MatButton} from "@angular/material/button";
import {FormlyFieldConfig, FormlyModule} from "@ngx-formly/core";


@Component({
  selector: 'app-edit-user-profile',
  standalone: true,
  imports: [CommonModule, NgxCommonModule, ReactiveFormsModule, TranslateModule, MatButton, FormlyModule],
  templateUrl: './edit-user-profile.component.html',
  styleUrls: ['./edit-user-profile.component.css']
})
export class EditUserProfileComponent extends EditUserProfileDirective {

  pageName = "EditUserProfile"

  formFields: FormlyFieldConfig[] = [
    {
      key: 'email',
      type: 'input',
      props: {
        label: this.translateService.instant('Email'),
        placeholder: 'name@company.com',
        disabled: true
      },
    },
    {
      fieldGroupClassName: "row",
      fieldGroup: [
        {
          key: 'first_name',
          type: 'input',
          className: "col-md-6 col-12",
          props: {
            label: this.translateService.instant('First name'),
            placeholder: '',
            required: true,
          },
        },
        {
          key: 'last_name',
          type: 'input',
          className: "col-md-6 col-12",
          props: {
            label: this.translateService.instant('Last name'),
            placeholder: '',
            required: true,
          },
        },
      ]
    },
    {
      fieldGroupClassName: "row",
      fieldGroup: [
        {
          key: 'birth_date',
          type: 'input',
          className: "col-md-6 col-12",
          props: {
            label: this.translateService.instant('Birth date'),
            placeholder: 'YYYY-MM-DD',
            type: 'date',
            required: false,
          },
        },
        {
          key: 'gender',
          type: 'select',
          className: "col-md-6 col-12",
          props: {
            label: this.translateService.instant('Gender'),
            placeholder: 'Select your gender',
            required: false,
            options: [
              {label: 'Male', value: 'male'},
              {label: 'Female', value: 'female'},
            ],
          }
        }
      ]
    }
  ];

  constructor(
    formBuilder: FormBuilder, userService: UserService,
    private translateService: TranslateService
  ) {
    super(formBuilder, userService);
  }


}

