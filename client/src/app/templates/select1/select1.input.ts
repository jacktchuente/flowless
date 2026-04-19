import {Component, OnInit} from '@angular/core';
import {Observable, of, Subject} from "rxjs";
import {MtxSelect} from "@ng-matero/extensions/select";
import {AsyncPipe} from "@angular/common";
import {ReactiveFormsModule} from "@angular/forms";
import {MatFormField, MatLabel} from "@angular/material/form-field";
import {MatInputModule} from "@angular/material/input";
import {FieldTypeConfig, FormlyModule} from "@ngx-formly/core";
import {FieldType} from "@ngx-formly/material";

@Component({
  selector: 'app-select1',
  standalone: true,
  imports: [
    MtxSelect,
    AsyncPipe,
    ReactiveFormsModule,
    FormlyModule,
    MatFormField,
    MatLabel,
    MatInputModule
  ],
  templateUrl: './select1.input.html',
  styleUrl: './select1.input.css'
})
export class Select1Input extends FieldType<FieldTypeConfig> implements OnInit {
  labelKey = 'label';
  valueKey = "value";
  clearable: boolean = false;
  multiple = false;
  label = "";
  items?: Observable<any> = of([]);

  onScrollToEnd: Subject<any> | undefined
  onSearch: Subject<any> | undefined

  ngOnInit() {
    const options = this.field.props?.options;

    if (options instanceof Observable) {
      this.items = options;
    } else {
      this.items = of(options || []);
    }
    this.labelKey = this.field.props?.['labelProp'] || this.labelKey;
    this.valueKey = this.field.props?.['valueProp'] || this.valueKey;
    this.clearable = this.field.props?.['clearable'] ?? this.clearable;
    this.multiple = this.field.props?.['multiple'] ?? this.multiple;

    this.onScrollToEnd = this.field.props?.['onScrollToEnd'] ?? this.onScrollToEnd;
    this.onSearch = this.field.props?.['onSearch'] ?? this.onSearch;

    this.label = this.field.props?.label || this.label
  }


  scrollToEnd($event: any) {
    this.onScrollToEnd?.next($event)
  }

  search($event: { term: string; items: any[] }) {
    this.onSearch?.next($event)
  }
}
