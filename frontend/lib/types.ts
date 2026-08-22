export type ConnectionState = "checking" | "connected" | "disconnected";
export type AppTheme = "solarized-light" | "light" | "dark" | "system";
export type InputType = "file" | "url";
export type ConverterName = "auto" | "pymupdf4llm" | "docling" | "markitdown";
export type ConversionMode = "fast" | "balanced" | "high_accuracy";
export interface ConversionOptions { converter: ConverterName; mode: ConversionMode; ocr: "auto" | "off" | "force"; images: "ignore" | "extract"; cpu: "balanced" | "maximum"; cache: boolean; }

export interface ConversionMetadata {
  original_filename: string;
  output_filename: string;
  pages: number | null;
  processing_seconds: number;
  figures: number;
  table_images: number;
  engine: string;
  engine_reason: string;
  warnings: string[];
  cache_hit: boolean;
  fallback_reason: string | null;
  input_type: InputType;
  source_url: string | null;
  source_domain: string | null;
}

export interface ConversionResult {
  result_id: string;
  markdown: string;
  markdown_url: string;
  package_url: string;
  metadata: ConversionMetadata;
}

export interface ApiErrorPayload {
  error?: { code?: string; message?: string };
  detail?: string | Array<{ msg?: string }>;
}

