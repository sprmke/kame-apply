import { z } from "zod";

/**
 * Zod issues become catalog keys (`validation.*`, optionally `key:param`), so schemas stay
 * language-free and the form layer translates them. See useZodForm.
 */
export default defineNuxtPlugin(() => {
  z.setErrorMap((issue, ctx) => {
    if (issue.code === "invalid_string" && issue.validation === "email") {
      return { message: ctx.data === "" ? "validation.required" : "validation.email" };
    }
    if (issue.code === "too_small" && issue.type === "string") {
      return {
        message:
          issue.minimum <= 1 ? "validation.required" : `validation.tooShort:${issue.minimum}`,
      };
    }
    if (issue.code === "too_big" && issue.type === "string")
      return { message: `validation.tooLong:${issue.maximum}` };
    if (issue.code === "invalid_type" && (ctx.data === undefined || ctx.data === null)) {
      return { message: "validation.required" };
    }
    return { message: "validation.invalid" };
  });
});
