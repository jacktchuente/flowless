import {Component, Inject} from '@angular/core';
import {DIALOG_DATA, DialogRef} from '@angular/cdk/dialog';
import {FlwModalComponent} from '../modal/flw-modal.component';
export interface FlwConfirmData {title:string;message:string;confirmLabel?:string}
@Component({standalone:true,imports:[FlwModalComponent],template:`<flw-modal [title]="data.title"><p>{{data.message}}</p><div modal-footer><button class="btn ghost" type="button" (click)="ref.close(false)">Annuler</button><button class="btn primary" type="button" (click)="ref.close(true)">{{data.confirmLabel||'Confirmer'}}</button></div></flw-modal>`})
export class FlwConfirmComponent {constructor(@Inject(DIALOG_DATA)public data:FlwConfirmData,public ref:DialogRef<boolean>){}}
