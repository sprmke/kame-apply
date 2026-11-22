import { createHash } from "node:crypto";

/** Primary checkout port. */
const DEFAULT_DEV_PORT = 3100;
const PORT_RANGE = 100;

function stickyPort() {
  const worktree = process.env.ORCA_WORKTREE_PATH;
  const root = process.env.ORCA_ROOT_PATH;
  if (!worktree || worktree === root) return DEFAULT_DEV_PORT;
  const hash = createHash("sha1").update(worktree).digest().readUInt16BE(0);
  return 3600 + (hash % PORT_RANGE);
}

/** Local Nuxt web port. The launcher bumps it on a collision. */
export const LOCAL_DEV_PORT = Number(process.env.LOCAL_DEV_PORT) || stickyPort();
