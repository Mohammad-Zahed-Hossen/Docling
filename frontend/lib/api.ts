import { CONNECTION_TIMEOUT_MS, CONVERSION_TIMEOUT_MS } from "./constants";
import type { ApiErrorPayload, ConversionOptions, ConversionResult } from "./types";

export class LocalEngineError extends Error {
  constructor(message: string, public readonly code: string) {
    super(message);
    this.name = "LocalEngineError";
  }
}

export function normalizeApiUrl(value: string): string {
  return value.trim().replace(/\/+$/, "");
}

export function resultUrl(apiUrl: string, path: string): string {
  return `${normalizeApiUrl(apiUrl)}${path.startsWith("/") ? path : `/${path}`}`;
}

export async function checkHealth(apiUrl: string): Promise<boolean> {
  const response = await fetchWithTimeout(resultUrl(apiUrl, "/api/health"), {}, CONNECTION_TIMEOUT_MS);
  if (!response.ok) return false;
  const value: unknown = await response.json();
  return isHealthResponse(value);
}

export async function checkHealthWithRetry(
  apiUrl: string,
  attempts: number,
  delayMs: number,
): Promise<boolean> {
  for (let attempt = 1; attempt <= attempts; attempt += 1) {
    try {
      if (await checkHealth(apiUrl)) return true;
    } catch {
      // The local engine may still be starting after Windows login.
    }
    if (attempt < attempts) await delay(delayMs);
  }
  return false;
}

export async function convertDocument(apiUrl: string, file: File, options: ConversionOptions): Promise<ConversionResult> {
  const data = new FormData();
  data.append("file", file);
  Object.entries(options).forEach(([key, value]) => data.append(key, String(value)));
  let response: Response;
  try {
    response = await fetchWithTimeout(
      resultUrl(apiUrl, "/api/convert"),
      { method: "POST", body: data },
      CONVERSION_TIMEOUT_MS,
    );
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") {
      throw new LocalEngineError("The local processing request timed out.", "TIMEOUT");
    }
    throw new LocalEngineError(
      "Could not connect to the local converter. Confirm it is running and that this site is allowed by CORS.",
      "LOCAL_ENGINE_ERROR",
    );
  }
  if (!response.ok) {
    let payload: ApiErrorPayload = {};
    try { payload = (await response.json()) as ApiErrorPayload; } catch { /* non-JSON response */ }
    throw new LocalEngineError(
      payload.error?.message ?? `The local engine returned HTTP ${response.status}.`,
      payload.error?.code ?? "LOCAL_ENGINE_ERROR",
    );
  }
  return (await response.json()) as ConversionResult;
}

export async function convertUrl(apiUrl: string, url: string, options: ConversionOptions): Promise<ConversionResult> {
  let response: Response;
  try {
    response = await fetchWithTimeout(resultUrl(apiUrl, "/api/convert-url"), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url: url.trim(), images: options.images, cache: options.cache }),
    }, CONVERSION_TIMEOUT_MS);
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") throw new LocalEngineError("The webpage request timed out.", "TIMEOUT");
    throw new LocalEngineError("Could not connect to the local converter.", "LOCAL_ENGINE_ERROR");
  }
  if (!response.ok) {
    let payload: ApiErrorPayload = {};
    try { payload = (await response.json()) as ApiErrorPayload; } catch { /* non-JSON response */ }
    throw new LocalEngineError(payload.error?.message ?? `The local engine returned HTTP ${response.status}.`, payload.error?.code ?? "LOCAL_ENGINE_ERROR");
  }
  return (await response.json()) as ConversionResult;
}

async function fetchWithTimeout(url: string, init: RequestInit, timeout: number): Promise<Response> {
  const controller = new AbortController();
  const timer = window.setTimeout(() => controller.abort(), timeout);
  try { return await fetch(url, { ...init, signal: controller.signal }); }
  finally { window.clearTimeout(timer); }
}

function isHealthResponse(value: unknown): value is { status: "ok" } {
  return typeof value === "object" && value !== null && "status" in value && value.status === "ok";
}

function delay(milliseconds: number): Promise<void> {
  return new Promise((resolve) => window.setTimeout(resolve, milliseconds));
}
