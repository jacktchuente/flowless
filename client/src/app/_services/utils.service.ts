import {Injectable} from '@angular/core';
import {BehaviorSubject, filter} from "rxjs";
import {NavigationEnd, Router} from "@angular/router";

@Injectable({
    providedIn: 'root'
})
export class UtilsService {

    public pageName$ = new BehaviorSubject<string>('');

    constructor(private router: Router) {
        this.subscribeToRouteChanges();
    }

    private subscribeToRouteChanges() {
        const routeToNameMap: { [key: string]: string } = {};
        this.router.events.pipe(
            filter(event => event instanceof NavigationEnd)
        ).subscribe((event: any) => {
            const name = routeToNameMap[event.urlAfterRedirects] || '';
            this.pageName$.next(name);
        });
    }
}
