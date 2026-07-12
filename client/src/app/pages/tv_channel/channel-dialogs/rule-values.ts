import {
  EditorialLineData,
  FormOptions,
  GridBlock,
} from "@project-interfaces/tv-channel";
import { FlwTagOption } from "../../../ui/tag-input/flw-tag-input.component";

export type RuleLevel = "allowed" | "preferred" | "forbidden";
export function ruleOptions(
  options: FormOptions,
  translate: (key: string, params?: Record<string, unknown>) => string,
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
export function readRuleValues(
  source: EditorialLineData | GridBlock,
  level: RuleLevel,
): Array<string | number> {
  return [
    ...source[`${level}_categories`].map((value) => `category:${value}`),
    ...source[`${level}_natures`].map((value) => `nature:${value}`),
    ...source[`${level}_container_kinds`].map((value) => `kind:${value}`),
  ];
}
export function writeRuleValues(
  target: Record<string, unknown>,
  level: RuleLevel,
  values: Array<string | number>,
) {
  target[`${level}_categories`] = values
    .filter((v) => String(v).startsWith("category:"))
    .map((v) => String(v).slice(9));
  target[`${level}_natures`] = values
    .filter((v) => String(v).startsWith("nature:"))
    .map((v) => Number(String(v).slice(7)));
  target[`${level}_container_kinds`] = values
    .filter((v) => String(v).startsWith("kind:"))
    .map((v) => Number(String(v).slice(5)));
}
