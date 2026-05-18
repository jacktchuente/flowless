import {Routes} from '@angular/router';
import {BaseComponent} from "./pages/base/base.component";
import {MediaSourceComponent} from "./pages/media_source/media-source/media-source.component";
import {MediaCollectionComponent} from "./pages/media_source/media-collection/media-collection.component";
import {MediaContainerComponent} from "./pages/media_source/media-container/media-container.component";
import {ChannelDetailComponent} from "./pages/tv_channel/channel-detail/channel-detail.component";
import {ChannelManagementComponent} from "./pages/tv_channel/channel-management/channel-management.component";

export const routes: Routes = [
    {path: '', pathMatch: 'full', redirectTo: 'app'},
    {
        path: 'app',
        component: BaseComponent,
        children: [
            {path: '', pathMatch: 'full', redirectTo: 'sources'},
            {path: 'sources', component: MediaSourceComponent},
            {path: 'collections', component: MediaCollectionComponent},
            {path: 'medias', component: MediaContainerComponent},
            {path: 'channels/:channelId', component: ChannelDetailComponent},
            {path: 'channels', component: ChannelManagementComponent},
        ]
    },
    {path: '**', redirectTo: 'app'}
]
