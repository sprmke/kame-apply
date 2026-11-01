/**
 * Cloudflare Email Routing → Worker → Kame API webhook.
 *
 * Bind EMAIL to this worker. Set secrets:
 *   KAME_API_BASE, KAME_WEBHOOK_SECRET
 *
 * The To address must be alerts+{token}@your-domain.
 */
export default {
  async email(message, env) {
    const raw = await new Response(message.raw).arrayBuffer();
    const bytes = new Uint8Array(raw);
    const to = String(message.to || "");
    const match = /alerts\+([A-Za-z0-9_-]+)@/i.exec(to);
    if (!match) {
      message.setReject("Unknown recipient");
      return;
    }
    const token = match[1];
    const body = bytes;
    const key = await crypto.subtle.importKey(
      "raw",
      new TextEncoder().encode(env.KAME_WEBHOOK_SECRET || ""),
      { name: "HMAC", hash: "SHA-256" },
      false,
      ["sign"],
    );
    const sig = await crypto.subtle.sign("HMAC", key, body);
    const hex = [...new Uint8Array(sig)].map((b) => b.toString(16).padStart(2, "0")).join("");
    const base = String(env.KAME_API_BASE || "").replace(/\/$/, "");
    await fetch(`${base}/api/v1/webhooks/inbound-email?token=${encodeURIComponent(token)}`, {
      method: "POST",
      headers: {
        "Content-Type": "application/octet-stream",
        "X-Kame-Signature": `sha256=${hex}`,
        "X-Inbound-Token": token,
      },
      body,
    });
  },
};
