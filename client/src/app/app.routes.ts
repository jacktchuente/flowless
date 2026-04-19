import {Routes} from '@angular/router';
import {AnonymousComponent} from "./pages/base/anonymous/anonymous.component";
import {AuthenticatedComponent} from "./pages/base/authenticated/authenticated.component";
import {AuthGuard} from "@kwyxyz/ngx-auth";

export const routes: Routes = [
    {
        path: '', component: AnonymousComponent, children: [
            // {path: '', component: LandingComponent},
            // {path: 'login', component: LoginComponent},
            // {path: 'login/:provider', component: LoginComponent},
            // {path: 'registration', component: RegistrationComponent},
            // {path: 'reset-password', component: ResetPasswordComponent},
            // {path: 'user-confirmation', component: UserConfirmationComponent},
            // {path: 'contact-us', component: ContactUsComponent},
            // {path: 'tos', component: TermOfServiceComponent},
            // {path: 'faq', component: FaqComponent},
            // {path: '404', component: NotFoundComponent},
            // {path: '500', component: NotFoundComponent},
            // {path: 'maintenance', component: MaintenanceComponent},
            // {path: 'logout', component: LogoutComponent}
        ]
    },
    {
        path: 'app', component: AuthenticatedComponent,
        canActivate: [AuthGuard],
        children: []
    },
    {path: '**', redirectTo: '/404'}

]
