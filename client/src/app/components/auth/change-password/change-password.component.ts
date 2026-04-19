import {Component} from '@angular/core';
import {CommonModule} from '@angular/common';
import {RouterLink, RouterOutlet} from "@angular/router";
import {NgxCommonModule} from "@kwyxyz/ngx-common";
import {ChangePasswordDirective, UserService} from "@kwyxyz/ngx-auth";
import {FormContainer1Component} from "../../../templates/form-container1/form-container1.component";
import {MatError, MatFormField, MatHint, MatLabel} from "@angular/material/form-field";
import {MatInput} from "@angular/material/input";
import {FormBuilder, ReactiveFormsModule} from "@angular/forms";
import {TranslateModule, TranslateService} from "@ngx-translate/core";
import {MatIcon} from "@angular/material/icon";
import {MatButton, MatIconButton} from "@angular/material/button";
import {FormlyFieldConfig, FormlyModule} from "@ngx-formly/core";


@Component({
  selector: 'app-change-password',
  standalone: true,
  imports: [CommonModule, RouterOutlet, FormContainer1Component,
    MatError, MatFormField, MatInput, MatLabel, NgxCommonModule, ReactiveFormsModule, RouterLink, TranslateModule, MatIcon, MatIconButton, MatHint, MatButton, FormlyModule],
  templateUrl: './change-password.component.html',
  styleUrls: ['./change-password.component.css']
})
export class ChangePasswordComponent extends ChangePasswordDirective {
  fields: FormlyFieldConfig[] = [
    {
      key: 'old_password',
      type: 'input',
      props: {
        type: 'password',
        label: 'Ancien mot de passe',
        placeholder: '',
      },
    },
    {
      validators: {
        validation: [
          {name: 'fieldMatch', options: {errorPath: 'new_password2', field1: 'new_password', field2: 'new_password2'}},
        ],
      },
      fieldGroup: [
        {
          key: 'new_password',
          type: 'input',
          props: {
            type: 'password',
            label: 'Nouveau mot de passe',
            placeholder: '',
          },
        },
        {
          key: 'new_password2',
          type: 'input',
          props: {
            type: 'password',
            label: 'Confirmation mot de passe',
            placeholder: '',
          },
        },
      ]
    },


  ];

  constructor(protected override formBuilder: FormBuilder,
              protected override userService: UserService,
              private translationService: TranslateService) {
    super(formBuilder, userService);
  }
}

