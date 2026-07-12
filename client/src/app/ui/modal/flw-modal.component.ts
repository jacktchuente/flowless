import {Component, Inject, Input, Optional} from '@angular/core';
import {DIALOG_DATA, DialogRef} from '@angular/cdk/dialog';
import {FlwIconComponent} from '../icon/flw-icon.component';
import {NgIf} from '@angular/common';

export interface FlwModalData { title?: string; description?: string; wide?: boolean }

@Component({selector:'flw-modal',standalone:true,imports:[FlwIconComponent,NgIf],template:`
  <section class="modal" [class.wide]="wide || data?.wide" role="dialog" aria-modal="true" [attr.aria-labelledby]="title ? 'flw-modal-title' : null">
    <header class="modal-head"><div><h3 id="flw-modal-title">{{title || data?.title}}</h3><p class="desc" *ngIf="description || data?.description">{{description || data?.description}}</p></div><button type="button" class="modal-close" aria-label="Fermer" (click)="close()"><flw-icon name="close"/></button></header>
    <div class="modal-body"><ng-content/></div>
    <footer class="modal-foot"><ng-content select="[modal-footer]"/></footer>
  </section>`,styles:[`:host{display:block}`]})
export class FlwModalComponent {
  @Input() title=''; @Input() description=''; @Input() wide=false;
  constructor(@Optional() public ref: DialogRef<unknown>, @Optional() @Inject(DIALOG_DATA) public data: FlwModalData|null) {}
  close(){this.ref?.close();}
}
