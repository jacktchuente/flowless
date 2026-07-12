import { Routes } from "@angular/router";
import { BaseComponent } from "./pages/base/base.component";

export const routes: Routes = [
  { path: "", pathMatch: "full", redirectTo: "app" },
  {
    path: "app",
    component: BaseComponent,
    children: [
      { path: "", pathMatch: "full", redirectTo: "overview" },
      {
        path: "overview",
        loadComponent: () =>
          import("./pages/overview/overview.component").then(
            (m) => m.OverviewComponent,
          ),
      },
      {
        path: "sources",
        loadComponent: () =>
          import("./pages/media_source/media-source/media-source.component").then(
            (m) => m.MediaSourceComponent,
          ),
      },
      {
        path: "collections",
        loadComponent: () =>
          import("./pages/media_source/media-collection/media-collection.component").then(
            (m) => m.MediaCollectionComponent,
          ),
      },
      {
        path: "medias",
        loadComponent: () =>
          import("./pages/media_source/media-container/media-container.component").then(
            (m) => m.MediaContainerComponent,
          ),
      },
      {
        path: "channels/:channelId",
        loadComponent: () =>
          import("./pages/tv_channel/channel-detail/channel-detail.component").then(
            (m) => m.ChannelDetailComponent,
          ),
      },
      {
        path: "channels",
        loadComponent: () =>
          import("./pages/tv_channel/channel-management/channel-management.component").then(
            (m) => m.ChannelManagementComponent,
          ),
      },
      {
        path: "editorial-planning",
        loadComponent: () =>
          import("./pages/editorial_planning/editorial-planning.component").then(
            (m) => m.EditorialPlanningComponent,
          ),
      },
    ],
  },
  { path: "**", redirectTo: "app" },
];
