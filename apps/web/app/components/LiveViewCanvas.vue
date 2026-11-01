<script setup lang="ts">
import { client } from "@kame/api-client";
import { FnButton, FnChip, useToast } from "@kame/ui";

const props = defineProps<{
  runId: string;
  openCheckpointKind?: string | null;
}>();

const { t } = useI18n();
const apiError = useApiError();
const toast = useToast();

const canvasRef = ref<HTMLCanvasElement | null>(null);
const connected = ref(false);
const controlMode = ref("agent");
const liveMode = ref("screencast");
const viewers = ref(0);
const fps = ref(0);
const amController = ref(false);
const connecting = ref(false);

let ws: WebSocket | null = null;
let pageW = 1280;
let pageH = 900;

const canInteract = computed(
  () => amController.value && (controlMode.value === "human" || !!props.openCheckpointKind),
);

async function connect() {
  if (connecting.value || !props.runId) return;
  connecting.value = true;
  try {
    const { data } = await client.post({
      url: `/api/v1/runs/${props.runId}/live/token`,
      throwOnError: true,
    });
    const token = (data as { token: string; ws_path: string }).token;
    const path = (data as { ws_path: string }).ws_path;
    const { public: cfg } = useRuntimeConfig();
    const apiBase = String(cfg.apiBase || "").replace(/\/$/, "");
    const wsBase = apiBase.replace(/^http/, "ws");
    ws = new WebSocket(`${wsBase}${path}?token=${encodeURIComponent(token)}`);
    ws.onopen = () => {
      connected.value = true;
    };
    ws.onclose = () => {
      connected.value = false;
      amController.value = false;
    };
    ws.onmessage = (ev) => {
      try {
        const msg = JSON.parse(String(ev.data));
        handleMsg(msg);
      } catch {
        /* ignore */
      }
    };
  } catch (e) {
    toast.push({ title: apiError(e), tone: "danger" });
  } finally {
    connecting.value = false;
  }
}

function handleMsg(msg: Record<string, unknown>) {
  const typ = String(msg.type || "");
  if (typ === "hello" || typ === "presence" || typ === "state") {
    if (msg.control_mode) controlMode.value = String(msg.control_mode);
    if (msg.live_mode) liveMode.value = String(msg.live_mode);
    if (typeof msg.viewers === "number") viewers.value = msg.viewers;
    if (typeof msg.fps === "number") fps.value = msg.fps;
    return;
  }
  if (typ === "frame" || typ === "screenshot") {
    const data = String(msg.data || "");
    const canvas = canvasRef.value;
    if (!canvas || !data) return;
    const img = new Image();
    img.onload = () => {
      pageW = img.width;
      pageH = img.height;
      const dpr = window.devicePixelRatio || 1;
      const cssW = canvas.clientWidth || img.width;
      const cssH = Math.round((cssW / img.width) * img.height);
      canvas.width = Math.floor(cssW * dpr);
      canvas.height = Math.floor(cssH * dpr);
      const ctx = canvas.getContext("2d");
      if (!ctx) return;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      ctx.drawImage(img, 0, 0, cssW, cssH);
      if (msg.seq != null && ws?.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ type: "ack", seq: msg.seq }));
      }
    };
    img.src = `data:image/jpeg;base64,${data}`;
  }
}

function pointerPos(e: PointerEvent) {
  const canvas = canvasRef.value;
  if (!canvas) return null;
  const rect = canvas.getBoundingClientRect();
  const x = ((e.clientX - rect.left) / rect.width) * pageW;
  const y = ((e.clientY - rect.top) / rect.height) * pageH;
  return { x, y };
}

function onPointer(e: PointerEvent) {
  if (!canInteract.value || !ws || ws.readyState !== WebSocket.OPEN) return;
  const p = pointerPos(e);
  if (!p) return;
  if (e.type === "pointerdown") {
    ws.send(JSON.stringify({ type: "input", kind: "mouse", x: p.x, y: p.y, button: "left" }));
  }
}

function onWheel(e: WheelEvent) {
  if (!canInteract.value || !ws || ws.readyState !== WebSocket.OPEN) return;
  e.preventDefault();
  const canvas = canvasRef.value;
  if (!canvas) return;
  const rect = canvas.getBoundingClientRect();
  const x = ((e.clientX - rect.left) / rect.width) * pageW;
  const y = ((e.clientY - rect.top) / rect.height) * pageH;
  ws.send(
    JSON.stringify({
      type: "input",
      kind: "scroll",
      x,
      y,
      deltaX: e.deltaX,
      deltaY: e.deltaY,
    }),
  );
}

async function onKey(e: KeyboardEvent) {
  if (!canInteract.value || !ws || ws.readyState !== WebSocket.OPEN) return;
  if (e.key.length === 1 && !e.metaKey && !e.ctrlKey) {
    e.preventDefault();
    ws.send(JSON.stringify({ type: "input", kind: "text", text: e.key }));
  }
}

async function onPaste(e: ClipboardEvent) {
  if (!canInteract.value || !ws || ws.readyState !== WebSocket.OPEN) return;
  const text = e.clipboardData?.getData("text") || "";
  if (!text) return;
  e.preventDefault();
  ws.send(JSON.stringify({ type: "input", kind: "paste", text }));
}

async function takeover() {
  try {
    await client.post({ url: `/api/v1/runs/${props.runId}/live/takeover`, throwOnError: true });
    amController.value = true;
    controlMode.value = "human";
    if (ws?.readyState === WebSocket.OPEN) ws.send(JSON.stringify({ type: "takeover" }));
  } catch (e) {
    toast.push({ title: apiError(e), tone: "danger" });
  }
}

async function handback() {
  try {
    await client.post({ url: `/api/v1/runs/${props.runId}/live/handback`, throwOnError: true });
    amController.value = false;
    controlMode.value = "agent";
    if (ws?.readyState === WebSocket.OPEN) ws.send(JSON.stringify({ type: "handback" }));
  } catch (e) {
    toast.push({ title: apiError(e), tone: "danger" });
  }
}

onMounted(() => {
  void connect();
});
onBeforeUnmount(() => {
  ws?.close();
  ws = null;
});

watch(
  () => props.runId,
  () => {
    ws?.close();
    void connect();
  },
);
</script>

<template>
  <section class="flex flex-col gap-2">
    <div class="flex flex-wrap items-center justify-between gap-2">
      <div class="flex flex-wrap items-center gap-2">
        <h2 class="text-sm font-medium tracking-wide text-ink-600 uppercase">
          {{ t("applications.liveView") }}
        </h2>
        <FnChip>{{ controlMode }}</FnChip>
        <span class="font-mono text-[0.6875rem] text-ink-600">{{ liveMode }}</span>
        <span v-if="connected" class="font-mono text-[0.6875rem] text-ink-600"
          >{{ fps.toFixed(0) }} fps · {{ viewers }}</span
        >
      </div>
      <div class="flex flex-wrap gap-2">
        <FnButton v-if="!amController" size="sm" :disabled="!connected" @click="takeover">{{
          t("applications.takeOver")
        }}</FnButton>
        <FnButton v-else size="sm" tone="quiet" @click="handback">{{
          t("applications.handBack")
        }}</FnButton>
      </div>
    </div>
    <p
      v-if="openCheckpointKind"
      class="border border-rule bg-paper-1 px-3 py-2 text-sm text-ink-900"
    >
      {{ openCheckpointKind }}
    </p>
    <canvas
      ref="canvasRef"
      class="w-full touch-none border border-rule bg-ink-900"
      tabindex="0"
      role="img"
      :aria-label="t('applications.liveView')"
      @pointerdown="onPointer"
      @wheel="onWheel"
      @keydown="onKey"
      @paste="onPaste"
    />
  </section>
</template>
