import {Component} from '@angular/core';
import {TranslateModule} from '@ngx-translate/core';
@Component({standalone:true,imports:[TranslateModule],template:`<header class="topline"><div><span class="eyebrow">{{'EDITORIAL_PLANNING.EYEBROW'|translate}}</span><h1>{{'EDITORIAL_PLANNING.TITLE'|translate}}</h1><p class="sub">{{'EDITORIAL_PLANNING.SUBTITLE'|translate}}</p></div></header><div class="content"><section class="card"><div class="empty">{{'EDITORIAL_PLANNING.LOADING'|translate}}</div></section></div>`}) export class EditorialPlanningComponent {}
