import { BehaviorSubject, Subject, of } from "rxjs";
import { ChannelImagesComponent } from "./channel-images.component";

describe("ChannelImagesComponent", () => {
  function build() {
    const channels = new BehaviorSubject<any[]>([]);
    const created: unknown[] = [];
    const chosen: Array<[unknown, unknown]> = [];
    const listRunsResponse = new Subject<{ isOk: boolean; body: unknown }>();
    const previewResponse = new Subject<{ isOk: boolean; body: unknown }>();

    const channelsService = {
      getObjectBehaviorSubject: () => channels,
      listObject: () => undefined,
      getImageQueryPreview: () => previewResponse,
    };
    const imageService = {
      listRuns: () => listRunsResponse,
      createRun: (payload: unknown) => {
        created.push(payload);
        return new Subject();
      },
      choose: (runId: unknown, suggestionId: unknown) => {
        chosen.push([runId, suggestionId]);
        return new Subject();
      },
      deleteRun: () => new Subject(),
    };
    const notified: string[] = [];
    const dialogs = { open: () => ({ closed: of(true) }) };
    const translate = { instant: (key: string) => key };
    const websocket = { crudEvent: new Subject() };

    let component!: ChannelImagesComponent;
    // Le constructeur consomme inject(DestroyRef): on instancie dans un
    // contexte d'injection minimal via TestBed serait plus lourd; on stub
    // takeUntilDestroyed en amont n'est pas necessaire car DestroyRef est
    // resolu par inject() -> on passe par TestBed.
    return {
      channels,
      created,
      chosen,
      listRunsResponse,
      previewResponse,
      notified,
      deps: { channelsService, imageService, dialogs, translate, websocket, notified },
      get component() {
        return component;
      },
      set component(value: ChannelImagesComponent) {
        component = value;
      },
    };
  }

  it("builds a run payload with the edited query and entity type", () => {
    const harness = build();
    const component = Object.create(
      ChannelImagesComponent.prototype,
    ) as ChannelImagesComponent;
    Object.assign(component, {
      selectedChannelId: "7",
      isSearching: false,
      runs: [],
      query: "Studio Ghibli",
      entityType: "studio",
      imageService: harness.deps.imageService,
      notification: { notify: (key: string) => harness.notified.push(key) },
    });

    component.search();

    expect(harness.created).toEqual([
      { tv_channel: "7", query: "Studio Ghibli", entity_type: "studio" },
    ]);
    expect(component.isSearching).toBeTrue();
  });

  it("omits the entity type when the query is empty (server resolves it)", () => {
    const harness = build();
    const component = Object.create(
      ChannelImagesComponent.prototype,
    ) as ChannelImagesComponent;
    Object.assign(component, {
      selectedChannelId: "7",
      isSearching: false,
      runs: [],
      query: "   ",
      entityType: "studio",
      imageService: harness.deps.imageService,
    });

    component.search();

    expect(harness.created).toEqual([
      { tv_channel: "7", query: "", entity_type: undefined },
    ]);
  });

  it("does not search while a run is in progress", () => {
    const harness = build();
    const component = Object.create(
      ChannelImagesComponent.prototype,
    ) as ChannelImagesComponent;
    Object.assign(component, {
      selectedChannelId: "7",
      isSearching: true,
      runs: [],
      query: "x",
      entityType: "theme",
      imageService: harness.deps.imageService,
    });

    component.search();

    expect(harness.created).toEqual([]);
  });

  it("choose asks confirmation then calls the API", () => {
    const harness = build();
    const component = Object.create(
      ChannelImagesComponent.prototype,
    ) as ChannelImagesComponent;
    Object.assign(component, {
      selectedChannelId: "7",
      isChoosing: false,
      runs: [],
      channels: [],
      imageService: harness.deps.imageService,
      dialogs: harness.deps.dialogs,
      translate: harness.deps.translate,
      notification: { notify: () => undefined },
      channelsService: harness.deps.channelsService,
    });

    component.choose({ id: 3 } as never, { id: 42 } as never);

    expect(harness.chosen).toEqual([[3, 42]]);
  });
});
