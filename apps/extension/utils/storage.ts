export type ExtSession = {
  token: string;
  workspaceId: string;
  apiBase: string;
  trackId?: string;
  profileId?: string;
};

const KEY = "kame.extension.session";

export async function getSession(): Promise<ExtSession | null> {
  const data = await browser.storage.local.get(KEY);
  const raw = data[KEY] as ExtSession | undefined;
  if (!raw?.token || !raw.workspaceId || !raw.apiBase) return null;
  return raw;
}

export async function setSession(session: ExtSession): Promise<void> {
  await browser.storage.local.set({ [KEY]: session });
}

export async function clearSession(): Promise<void> {
  await browser.storage.local.remove(KEY);
}
