import { ref } from "vue";

export type ToastTone = "neutral" | "success" | "danger";
export type ToastItem = { id: number; title: string; description?: string; tone: ToastTone };

const toasts = ref<ToastItem[]>([]);
let next = 1;

export function useToast() {
  function push(t: Omit<ToastItem, "id" | "tone"> & { tone?: ToastTone }): number {
    const id = next++;
    toasts.value.push({ tone: "neutral", ...t, id });
    return id;
  }
  function dismiss(id: number) {
    toasts.value = toasts.value.filter((t) => t.id !== id);
  }
  return { toasts, push, dismiss };
}
