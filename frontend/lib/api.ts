import { CONNECTION_TIMEOUT_MS, CONVERSION_TIMEOUT_MS } from "./constants";
import type { ApiErrorPayload, ConversionResult } from "./types";

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

export async function convertPdf(apiUrl: string, file: File): Promise<ConversionResult> {
  const data = new FormData();
  data.append("file", file);
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
      "Could not connect to the local Docling engine. Confirm it is running and that this site is allowed by CORS.",
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

async function fetchWithTimeout(url: string, init: RequestInit, timeout: number): Promise<Response> {
  const controller = new AbortController();
  const timer = window.setTimeout(() => controller.abort(), timeout);
  try { return await fetch(url, { ...init, signal: controller.signal }); }
  finally { window.clearTimeout(timer); }
}

function isHealthResponse(value: unknown): value is { status: "ok" } {
  return typeof value === "object" && value !== null && "status" in value && value.status === "ok";
}
