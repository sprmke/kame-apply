/**
 * Reka UI refuses an empty string as a `SelectItem` value. A select still needs a way to model
 * "no choice", so empty values travel through the component as a sentinel.
 */
export const EMPTY_OPTION = "__fn_empty__";

export function toItemValue(value: string): string {
  return value === "" ? EMPTY_OPTION : value;
}

export function fromItemValue(value: string): string {
  return value === EMPTY_OPTION ? "" : value;
}
