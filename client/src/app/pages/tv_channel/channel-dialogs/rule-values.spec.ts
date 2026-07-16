import { EditorialLineData, FormOptions } from "@project-interfaces/tv-channel";
import { readRuleValues, ruleOptions, writeRuleValues } from "./rule-values";

describe("unified rule values", () => {
  const options: FormOptions = {
    categories: ["crime"],
    natures: [{ value: 1, label: "fiction" }],
    container_kinds: [{ value: 2, label: "series" }],
    programming_roles: [],
    filler_policies: [],
  };
  const line: EditorialLineData = {
    allowed: { categories: ["crime"], natures: [1], container_kinds: [2] },
    preferred: {},
    forbidden: {},
    start_at: "18:00:00",
    end_at: "23:00:00",
    allow_filler: true,
  };

  it("combines and redistributes typed tags", () => {
    expect(
      ruleOptions(options, (key, params) =>
        params?.["value"] ? `${key}:${params["value"]}` : key,
      ).map((option) => option.value),
    ).toEqual(["category:crime", "nature:1", "kind:2"]);
    const values = readRuleValues(line, "allowed");
    const payload: Record<string, unknown> = {};
    writeRuleValues(payload, "allowed", values);
    expect(payload).toEqual({
      allowed: { categories: ["crime"], natures: [1], container_kinds: [2] },
    });
  });
});
