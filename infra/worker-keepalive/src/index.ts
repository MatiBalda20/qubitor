/**
 * Keep-alive de los servicios de Qubitor en Render (plan free).
 *
 * En cada disparo del Cron Trigger hace GET a <url>/health de cada URL de
 * TARGETS (definida en [vars] de wrangler.toml), en paralelo y con timeout.
 * Loguea el resultado de cada una; si una falla, las demás siguen igual.
 */

export interface Env {
  /** URLs base separadas por coma, sin "/health". */
  TARGETS: string;
  /** Timeout por pedido en milisegundos. */
  TIMEOUT_MS?: string;
}

const DEFAULT_TIMEOUT_MS = 30_000;

interface PingResult {
  url: string;
  ok: boolean;
  status?: number;
  ms: number;
  error?: string;
}

export function parseTargets(raw: string | undefined): string[] {
  return (raw ?? "")
    .split(",")
    .map((u) => u.trim().replace(/\/+$/, ""))
    .filter((u) => u.length > 0)
    .map((u) => `${u}/health`);
}

function parseTimeout(raw: string | undefined): number {
  const n = Number(raw);
  return Number.isFinite(n) && n > 0 ? n : DEFAULT_TIMEOUT_MS;
}

async function ping(url: string, timeoutMs: number): Promise<PingResult> {
  const start = Date.now();
  try {
    const res = await fetch(url, {
      method: "GET",
      headers: { "user-agent": "qubitor-keepalive" },
      signal: AbortSignal.timeout(timeoutMs),
    });
    // Se descarta el cuerpo para liberar la conexión.
    await res.body?.cancel();
    return { url, ok: res.ok, status: res.status, ms: Date.now() - start };
  } catch (err) {
    const error =
      err instanceof Error && (err.name === "TimeoutError" || err.name === "AbortError")
        ? `timeout tras ${timeoutMs} ms`
        : String(err);
    return { url, ok: false, ms: Date.now() - start, error };
  }
}

export default {
  async scheduled(controller: ScheduledController, env: Env): Promise<void> {
    const targets = parseTargets(env.TARGETS);
    if (targets.length === 0) {
      console.warn("keepalive: TARGETS está vacío, no hay nada que pingear");
      return;
    }

    const timeoutMs = parseTimeout(env.TIMEOUT_MS);
    const results = await Promise.all(targets.map((url) => ping(url, timeoutMs)));

    for (const r of results) {
      const line = JSON.stringify({ cron: controller.cron, ...r });
      if (r.ok) console.log(`keepalive ok ${line}`);
      else console.error(`keepalive fail ${line}`);
    }
  },
} satisfies ExportedHandler<Env>;
