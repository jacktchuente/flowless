import {Injectable} from '@angular/core';
import {TranslateService} from '@ngx-translate/core';
import {ToastService} from '../../ui/toast/toast.service';
@Injectable({providedIn:'root'})
export class NotificationService {constructor(private toast:ToastService,private translate:TranslateService){}notify(message:string,duration=10000){this.translate.get(message).subscribe(text=>this.toast.show(text||message,{kind:'info',duration}))}}
