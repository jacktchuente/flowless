import {Component} from '@angular/core';
import {TranslateModule} from '@ngx-translate/core';
@Component({standalone:true,imports:[TranslateModule],template:`<header class="topline"><div><span class="eyebrow">{{'OVERVIEW.EYEBROW'|translate}}</span><h1>{{'OVERVIEW.TITLE'|translate}}</h1><p class="sub">{{'OVERVIEW.LOADING'|translate}}</p></div></header><div class="content"><section class="card"><div class="empty">{{'OVERVIEW.LOADING'|translate}}</div></section></div>`}) export class OverviewComponent {}
