import {Component, EventEmitter, forwardRef, Input, Output} from '@angular/core';
import {ControlValueAccessor, NG_VALUE_ACCESSOR} from '@angular/forms';
import {NgIf} from '@angular/common';

@Component({selector:'flw-switch',standalone:true,imports:[NgIf],template:`<label class="switch"><input type="checkbox" [checked]="value" [disabled]="disabled" (change)="set($any($event.target).checked)" (blur)="touched()"><span class="track"></span><span class="lbl" *ngIf="label">{{label}}</span></label>`,providers:[{provide:NG_VALUE_ACCESSOR,useExisting:forwardRef(()=>FlwSwitchComponent),multi:true}]})
export class FlwSwitchComponent implements ControlValueAccessor {@Input() label='';@Input() value=false;@Output() valueChange=new EventEmitter<boolean>();disabled=false;private change=(v:boolean)=>{};touched=()=>{};writeValue(v:boolean){this.value=!!v}registerOnChange(fn:(v:boolean)=>void){this.change=fn}registerOnTouched(fn:()=>void){this.touched=fn}setDisabledState(v:boolean){this.disabled=v}set(v:boolean){this.value=v;this.change(v);this.valueChange.emit(v)}}
