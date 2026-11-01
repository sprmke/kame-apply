export type Platform =
  | "linkedin"
  | "indeed"
  | "jobstreet"
  | "seek"
  | "greenhouse"
  | "lever"
  | "ashby"
  | "workday"
  | "workable"
  | "smartrecruiters"
  | "generic";

export function detectPlatform(url: string): Platform {
  const u = (url || "").toLowerCase();
  if (u.includes("linkedin.com")) return "linkedin";
  if (u.includes("indeed.")) return "indeed";
  if (u.includes("jobstreet.")) return "jobstreet";
  if (u.includes("seek.com") || u.includes("seek.co.")) return "seek";
  if (u.includes("greenhouse.io") || u.includes("boards.greenhouse")) return "greenhouse";
  if (u.includes("jobs.lever.co") || u.includes("lever.co")) return "lever";
  if (u.includes("ashbyhq.com")) return "ashby";
  if (u.includes("myworkdayjobs.com") || u.includes("workday.com")) return "workday";
  if (u.includes("workable.com")) return "workable";
  if (u.includes("smartrecruiters.com")) return "smartrecruiters";
  return "generic";
}

export const RESTRICTED: Platform[] = ["linkedin", "indeed", "jobstreet", "seek"];

export function isConfirmationUrl(url: string, platform: Platform): boolean {
  const u = url.toLowerCase();
  if (platform === "greenhouse" && /confirmation|thanks|thank-you|submitted/.test(u)) return true;
  if (platform === "lever" && /thanks|confirmation/.test(u)) return true;
  if (platform === "linkedin" && /easy-apply.*submitted|application-submitted/.test(u)) return true;
  if (/\/applied|application.?confirm|thank.?you|confirmation/.test(u)) return true;
  return false;
}
