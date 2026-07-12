import { TestBed } from "@angular/core/testing";
import { provideHttpClient } from "@angular/common/http";
import { TranslateModule } from "@ngx-translate/core";
import { NgxRequestModule } from "@kwyxyz/ngx-request";
import { NotificationService } from "@project-shared/services/notification.service";
import { MediaSourceService } from "@project-services/media-source.service";
import { CatalogService } from "@project-services/catalog.service";
import { FlwConfirmationService } from "./confirmation.service";
import { FlwLoadingService } from "./loading.service";

// Reproduit le câblage de InitialModule : sans confirmationService/loadingService,
// les factories PartialConfirmationService/PartialLoadingService de ngx-request
// font inj.get(undefined) et toute construction d'ObjectApiService explose.
describe("ngx-request DI wiring", () => {
  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [
        TranslateModule.forRoot(),
        NgxRequestModule.forRoot({
          defaultApiUrl: "http://localhost:9876/api",
          notificationService: NotificationService,
          confirmationService: FlwConfirmationService,
          loadingService: FlwLoadingService,
          defaultWsUrl: "ws://localhost:9876",
          defaultPublicWs: "public",
          userSocketUrl: "user-socket/me",
          dateFields: [],
        }),
      ],
      providers: [provideHttpClient()],
    });
  });

  it("constructs ObjectApiServices without crashing", () => {
    expect(TestBed.inject(MediaSourceService)).toBeTruthy();
    expect(TestBed.inject(CatalogService)).toBeTruthy();
  });

  it("tracks concurrent requests in FlwLoadingService", () => {
    const loading = TestBed.inject(FlwLoadingService);
    let state = false;
    loading.loading$.subscribe((value) => (state = value));
    loading.loading(true);
    loading.loading(true);
    loading.loading(false);
    expect(state).toBeTrue();
    loading.loading(false);
    expect(state).toBeFalse();
  });
});
