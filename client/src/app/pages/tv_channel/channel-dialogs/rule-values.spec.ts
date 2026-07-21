import { EditorialLineData, FormOptions } from "@project-interfaces/tv-channel";
import {
  readRuleValues,
  parseNumericComparison,
  parseRuleOptionSearch,
  ruleOptions,
  ruleValueLabel,
  searchResultToOption,
  writeRuleValues,
} from "./rule-values";

describe("unified rule values", () => {
  const options: FormOptions = {
    categories: ["crime"],
    natures: [{ value: 1, label: "fiction" }],
    container_kinds: [{ value: 2, label: "series" }],
    programming_roles: [],
    filler_policies: [],
  };
  const line: EditorialLineData = {
    allowed: {
      categories: ["crime"],
      genres: ["Film noir"],
      tags: ["Late night"],
      comparisons: [
        { field: "min_age", operator: "gt", value: 10 },
        { field: "star_rating", operator: "gte", value: 4 },
      ],
      natures: [1],
      container_kinds: [2],
    },
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
      allowed: {
        categories: ["crime"],
        natures: [1],
        container_kinds: [2],
        genres: ["Film noir"],
        tags: ["Late night"],
        directors: [],
        writers: [],
        creators: [],
        actors: [],
        studios: [],
        countries: [],
        audio_languages: [],
        subtitle_languages: [],
        comparisons: [
          { field: "min_age", operator: "gt", value: 10 },
          { field: "star_rating", operator: "gte", value: 4 },
        ],
      },
    });
  });

  it("maps genre and tag search results to typed tags", () => {
    const translate = (_key: string, params?: Record<string, unknown>) =>
      String(params?.["value"] ?? "");

    expect(
      searchResultToOption({ axis: "genres", value: "Film noir" }, translate),
    ).toEqual({
      label: "Film noir",
      value: "genre:Film noir",
    });
    expect(
      searchResultToOption({ axis: "tags", value: "Late night" }, translate),
    ).toEqual({
      label: "Late night",
      value: "tag:Late night",
    });
    expect(ruleValueLabel("genre:Film noir", translate)).toBe("Film noir");
  });

  it("parses and canonicalizes numeric filter expressions", () => {
    expect(parseNumericComparison(" min-age > 10 ")).toEqual({
      label: "min-age>10",
      value: "comparison:min_age:gt:10",
    });
    expect(parseNumericComparison("overall-rating >= 8,5")).toEqual({
      label: "rating>=8.5",
      value: "comparison:overall_rating_score:gte:8.5",
    });
    expect(parseNumericComparison("stars>=4")).toEqual({
      label: "stars>=4",
      value: "comparison:star_rating:gte:4",
    });
  });

  it("rejects invalid numeric filter expressions", () => {
    expect(parseNumericComparison("min-age>10.5")).toBeNull();
    expect(parseNumericComparison("stars>6")).toBeNull();
    expect(parseNumericComparison("unknown>10")).toBeNull();
  });

  it("routes prefixed autocomplete searches to their vocabulary axis", () => {
    expect(parseRuleOptionSearch("genre=")).toEqual({ axis: "genres", query: "" });
    expect(parseRuleOptionSearch("Genre= noir ")).toEqual({ axis: "genres", query: "noir" });
    expect(parseRuleOptionSearch("tag=night")).toEqual({ axis: "tags", query: "night" });
    expect(parseRuleOptionSearch("tom")).toEqual({ query: "tom" });
  });
});
