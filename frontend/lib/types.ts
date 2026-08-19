export type ConnectionState = "checking" | "connected" | "disconnected";

export interface ConversionMetadata {
  original_filename: string;
  output_filename: string;
  pages: number | null;
  processing_seconds: number;
  figures: number;
  table_images: number;
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
}
