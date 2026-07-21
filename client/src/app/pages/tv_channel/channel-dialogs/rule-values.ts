import {
  EditorialLineData,
  FormOptions,
  GridBlock,
  NumericComparison,
  NumericComparisonOperator,
  RuleOptionSearchResult,
} from "@project-interfaces/tv-channel";
import { FlwTagOption } from "../../../ui/tag-input/flw-tag-input.component";

export type RuleLevel = "allowed" | "preferred" | "forbidden";
export type TranslateFn = (
  key: string,
  params?: Record<string, unknown>,
) => string;

// Axes a valeurs ouvertes servis par l'endpoint rule-option-search. Les
// valeurs de tag restent encodees "prefix:valeur" comme les axes historiques.
const VOCABULARY_AXES: Array<{
  axis: keyof EditorialLineData["allowed"] & string;
  prefix: string;
  labelKey: string;
  isLanguage?: boolean;
}> = [
  {
    axis: "genres",
    prefix: "genre",
    labelKey: "CHANNEL_DIALOGS.COMMON.GENRE_VALUE",
  },
  {
    axis: "tags",
    prefix: "tag",
    labelKey: "CHANNEL_DIALOGS.COMMON.TAG_VALUE",
  },
  {
    axis: "directors",
    prefix: "director",
    labelKey: "CHANNEL_DIALOGS.COMMON.DIRECTOR_VALUE",
  },
  {
    axis: "writers",
    prefix: "writer",
    labelKey: "CHANNEL_DIALOGS.COMMON.WRITER_VALUE",
  },
  {
    axis: "creators",
    prefix: "creator",
    labelKey: "CHANNEL_DIALOGS.COMMON.CREATOR_VALUE",
  },
  {
    axis: "actors",
    prefix: "actor",
    labelKey: "CHANNEL_DIALOGS.COMMON.ACTOR_VALUE",
  },
  {
    axis: "studios",
    prefix: "studio",
    labelKey: "CHANNEL_DIALOGS.COMMON.STUDIO_VALUE",
  },
  {
    axis: "countries",
    prefix: "country",
    labelKey: "CHANNEL_DIALOGS.COMMON.COUNTRY_VALUE",
  },
  {
    axis: "audio_languages",
    prefix: "audio_language",
    labelKey: "CHANNEL_DIALOGS.COMMON.AUDIO_LANGUAGE_VALUE",
    isLanguage: true,
  },
  {
    axis: "subtitle_languages",
    prefix: "subtitle_language",
    labelKey: "CHANNEL_DIALOGS.COMMON.SUBTITLE_LANGUAGE_VALUE",
    isLanguage: true,
  },
];

const AXIS_BY_NAME = new Map<string, (typeof VOCABULARY_AXES)[number]>(
  VOCABULARY_AXES.map((spec) => [spec.axis, spec]),
);

interface NumericFieldSpec {
  field: string;
  inputName: string;
  aliases: string[];
  integer: boolean;
  minimum: number;
  maximum: number;
}

const NUMERIC_FIELDS: NumericFieldSpec[] = [
  {
    field: "min_age",
    inputName: "min-age",
    aliases: ["min-age"],
    integer: true,
    minimum: 0,
    maximum: 100,
  },
  {
    field: "max_age",
    inputName: "max-age",
    aliases: ["max-age"],
    integer: true,
    minimum: 0,
    maximum: 100,
  },
  {
    field: "release_year",
    inputName: "release-year",
    aliases: ["release-year"],
    integer: true,
    minimum: 1800,
    maximum: 3000,
  },
  {
    field: "overall_rating_score",
    inputName: "rating",
    aliases: ["rating", "overall-rating"],
    integer: false,
    minimum: 0,
    maximum: 10,
  },
  {
    field: "community_rating_score",
    inputName: "community-rating",
    aliases: ["community-rating"],
    integer: false,
    minimum: 0,
    maximum: 10,
  },
  {
    field: "critic_rating_score",
    inputName: "critic-rating",
    aliases: ["critic-rating"],
    integer: false,
    minimum: 0,
    maximum: 100,
  },
  {
    field: "star_rating",
    inputName: "stars",
    aliases: ["stars"],
    integer: false,
    minimum: 0,
    maximum: 5,
  },
  {
    field: "item_count",
    inputName: "item-count",
    aliases: ["item-count"],
    integer: true,
    minimum: 0,
    maximum: 1_000_000,
  },
  {
    field: "duration_min_seconds",
    inputName: "min-duration-seconds",
    aliases: ["min-duration-seconds"],
    integer: true,
    minimum: 0,
    maximum: 100_000_000,
  },
  {
    field: "duration_max_seconds",
    inputName: "max-duration-seconds",
    aliases: ["max-duration-seconds"],
    integer: true,
    minimum: 0,
    maximum: 100_000_000,
  },
  {
    field: "total_duration_seconds",
    inputName: "total-duration-seconds",
    aliases: ["total-duration-seconds"],
    integer: true,
    minimum: 0,
    maximum: 1_000_000_000,
  },
  {
    field: "min_video_width",
    inputName: "min-video-width",
    aliases: ["min-video-width"],
    integer: true,
    minimum: 0,
    maximum: 100_000,
  },
  {
    field: "min_video_height",
    inputName: "min-video-height",
    aliases: ["min-video-height"],
    integer: true,
    minimum: 0,
    maximum: 100_000,
  },
];
const NUMERIC_FIELD_BY_ALIAS = new Map(
  NUMERIC_FIELDS.flatMap((spec) =>
    spec.aliases.map((alias) => [alias, spec] as const),
  ),
);
const NUMERIC_FIELD_BY_NAME = new Map(
  NUMERIC_FIELDS.map((spec) => [spec.field, spec]),
);
const OPERATOR_BY_SYMBOL: Record<string, NumericComparisonOperator> = {
  ">": "gt",
  ">=": "gte",
  "<": "lt",
  "<=": "lte",
  "=": "eq",
  "==": "eq",
  "!=": "neq",
};
const SYMBOL_BY_OPERATOR: Record<NumericComparisonOperator, string> = {
  gt: ">",
  gte: ">=",
  lt: "<",
  lte: "<=",
  eq: "=",
  neq: "!=",
};
const COMPARISON_PREFIX = "comparison";

export function parseNumericComparison(text: string): FlwTagOption | null {
  const match = text
    .trim()
    .toLowerCase()
    .match(/^([a-z][a-z0-9-]*)\s*(>=|<=|!=|==|>|<|=)\s*(-?\d+(?:[.,]\d+)?)$/);
  if (!match) return null;
  const spec = NUMERIC_FIELD_BY_ALIAS.get(match[1]);
  const operator = OPERATOR_BY_SYMBOL[match[2]];
  const value = Number(match[3].replace(",", "."));
  if (!spec || !operator || !Number.isFinite(value)) return null;
  if (spec.integer && !Number.isInteger(value)) return null;
  if (value < spec.minimum || value > spec.maximum) return null;
  const comparison: NumericComparison = { field: spec.field, operator, value };
  return {
    label: numericComparisonLabel(comparison),
    value: encodeComparison(comparison),
  };
}

export function numericComparisonLabel(comparison: NumericComparison): string {
  const spec = NUMERIC_FIELD_BY_NAME.get(comparison.field);
  return `${spec?.inputName ?? comparison.field}${SYMBOL_BY_OPERATOR[comparison.operator]}${comparison.value}`;
}

function encodeComparison(comparison: NumericComparison): string {
  return `${COMPARISON_PREFIX}:${comparison.field}:${comparison.operator}:${comparison.value}`;
}

function decodeComparison(value: string | number): NumericComparison | null {
  const [prefix, field, operator, rawValue] = String(value).split(":");
  if (prefix !== COMPARISON_PREFIX || !NUMERIC_FIELD_BY_NAME.has(field))
    return null;
  if (
    !Object.values(OPERATOR_BY_SYMBOL).includes(
      operator as NumericComparisonOperator,
    )
  )
    return null;
  const number = Number(rawValue);
  if (!Number.isFinite(number)) return null;
  return {
    field,
    operator: operator as NumericComparisonOperator,
    value: number,
  };
}

export function ruleOptions(
  options: FormOptions,
  translate: TranslateFn,
): FlwTagOption[] {
  return [
    ...options.categories.map((value) => ({
      label: translate("CHANNEL_DIALOGS.COMMON.CATEGORY_VALUE", { value }),
      value: `category:${value}`,
    })),
    ...options.natures.map((option) => ({
      label: translate("CHANNEL_DIALOGS.COMMON.NATURE_VALUE", {
        value: translate(`UI.NATURES.${option.value}`),
      }),
      value: `nature:${option.value}`,
    })),
    ...options.container_kinds.map((option) => ({
      label: translate("CHANNEL_DIALOGS.COMMON.KIND_VALUE", {
        value: translate(`UI.CONTAINER_KINDS.${option.value}`),
      }),
      value: `kind:${option.value}`,
    })),
  ];
}

export function searchResultToOption(
  result: RuleOptionSearchResult,
  translate: TranslateFn,
  locale?: string,
): FlwTagOption | null {
  const spec = AXIS_BY_NAME.get(result.axis);
  if (!spec) return null;
  return {
    label: translate(spec.labelKey, {
      value: spec.isLanguage
        ? languageDisplayName(result.value, locale)
        : result.value,
    }),
    value: `${spec.prefix}:${result.value}`,
  };
}

// Libelle d'un tag encode sans dependre des options statiques : necessaire
// pour afficher les valeurs sauvegardees des axes servis par la recherche.
export function ruleValueLabel(
  value: string | number,
  translate: TranslateFn,
  locale?: string,
): string {
  const text = String(value);
  const comparison = decodeComparison(text);
  if (comparison) return numericComparisonLabel(comparison);
  const separator = text.indexOf(":");
  if (separator <= 0) return text;
  const prefix = text.slice(0, separator);
  const raw = text.slice(separator + 1);
  if (prefix === "category")
    return translate("CHANNEL_DIALOGS.COMMON.CATEGORY_VALUE", { value: raw });
  if (prefix === "nature")
    return translate("CHANNEL_DIALOGS.COMMON.NATURE_VALUE", {
      value: translate(`UI.NATURES.${raw}`),
    });
  if (prefix === "kind")
    return translate("CHANNEL_DIALOGS.COMMON.KIND_VALUE", {
      value: translate(`UI.CONTAINER_KINDS.${raw}`),
    });
  const spec = VOCABULARY_AXES.find((entry) => entry.prefix === prefix);
  if (!spec) return text;
  return translate(spec.labelKey, {
    value: spec.isLanguage ? languageDisplayName(raw, locale) : raw,
  });
}

function languageDisplayName(code: string, locale?: string): string {
  try {
    const displayNames = new Intl.DisplayNames([locale || "en"], {
      type: "language",
    });
    return displayNames.of(code) ?? code;
  } catch {
    // Codes hors BCP47 (ex. ISO 639-2/B "fre") : on garde le code brut.
    return code;
  }
}

export function readRuleValues(
  source: EditorialLineData | GridBlock,
  level: RuleLevel,
): Array<string | number> {
  const rules = source[level] ?? {};
  return [
    ...(rules.categories ?? []).map((value) => `category:${value}`),
    ...(rules.natures ?? []).map((value) => `nature:${value}`),
    ...(rules.container_kinds ?? []).map((value) => `kind:${value}`),
    ...VOCABULARY_AXES.flatMap((spec) =>
      ((rules[spec.axis] as string[] | undefined) ?? []).map(
        (value) => `${spec.prefix}:${value}`,
      ),
    ),
    ...(rules.comparisons ?? []).map(encodeComparison),
  ];
}

export function writeRuleValues(
  target: Record<string, unknown>,
  level: RuleLevel,
  values: Array<string | number>,
) {
  const byPrefix = (prefix: string) =>
    values
      .filter((v) => String(v).startsWith(`${prefix}:`))
      .map((v) => String(v).slice(prefix.length + 1));
  target[level] = {
    categories: byPrefix("category"),
    natures: byPrefix("nature").map(Number),
    container_kinds: byPrefix("kind").map(Number),
    ...Object.fromEntries(
      VOCABULARY_AXES.map((spec) => [spec.axis, byPrefix(spec.prefix)]),
    ),
    comparisons: values
      .map(decodeComparison)
      .filter(
        (comparison): comparison is NumericComparison => comparison !== null,
      ),
  };
}
