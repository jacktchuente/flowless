import { Subject } from "rxjs";
import { FormOptions, MarathonConfigData } from "@project-interfaces/tv-channel";
import { MarathonConfigDialogComponent } from "./marathon-config-dialog.component";

describe("MarathonConfigDialogComponent", () => {
  const formOptions: FormOptions = {
    categories: [],
    natures: [],
    container_kinds: [
      { value: 1, label: "standalone_video" },
      { value: 2, label: "series" },
      { value: 4, label: "music_video_release" },
    ],
    programming_roles: [],
    filler_policies: [],
  };

  function build(policies = [{ container_kind: 2, min_run: 2, max_run: 2, quota: 1 }]) {
    const saved: MarathonConfigData[] = [];
    const response = new Subject<{ isOk: boolean; body: unknown }>();
    const service = {
      updateMarathonConfig: (_id: unknown, payload: MarathonConfigData) => {
        saved.push(payload);
        return response;
      },
    };
    const notified: string[] = [];
    const closed: unknown[] = [];
    const component = new MarathonConfigDialogComponent(
      service as never,
      { notify: (key: string) => notified.push(key) } as never,
      { close: (value: unknown) => closed.push(value) } as never,
      { channelId: 1, policies, formOptions },
    );
    return { component, saved, response, notified, closed };
  }

  it("excludes kinds already used from the add options", () => {
    const { component } = build();
    expect(component.availableKinds().map((option) => option.value)).toEqual([
      1, 4,
    ]);
    component.addRow();
    expect(component.policies.length).toBe(2);
    expect(component.policies[1].container_kind).toBe(1);
    expect(component.availableKinds().map((option) => option.value)).toEqual([
      4,
    ]);
  });

  it("keeps the current kind selectable in its own row", () => {
    const { component } = build();
    expect(
      component.kindOptions(component.policies[0]).map((o) => o.value),
    ).toEqual([1, 2, 4]);
  });

  it("rejects min_run above max_run before calling the API", () => {
    const { component, saved } = build([
      { container_kind: 2, min_run: 3, max_run: 2, quota: 1 },
    ]);
    component.save();
    expect(component.error).toBe("CHANNEL_DIALOGS.MARATHON.MIN_ABOVE_MAX");
    expect(saved.length).toBe(0);
  });

  it("saves a cleaned payload and closes on success", () => {
    const { component, saved, response, closed } = build();
    component.policies[0].quota = 3;
    component.save();
    expect(saved).toEqual([
      { kind_policies: [{ container_kind: 2, min_run: 2, max_run: 2, quota: 3 }] },
    ]);
    response.next({ isOk: true, body: null });
    expect(closed).toEqual([true]);
  });
});
