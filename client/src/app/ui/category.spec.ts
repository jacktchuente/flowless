import { containerKindLabel, natureLabel, natureToCategory } from "./category";

describe("category helpers", () => {
  it("maps serialized integer natures to timeline categories", () => {
    expect(natureToCategory(1)).toBe("fiction");
    expect(natureToCategory(4)).toBe("sport");
    expect(natureToCategory(6)).toBe("comedy");
    expect(natureToCategory(99)).toBe("filler");
  });

  it("resolves nature and container labels", () => {
    expect(natureLabel(2)).toBe("UI.NATURES.2");
    expect(containerKindLabel(2)).toBe("UI.CONTAINER_KINDS.2");
  });
});
