/**
 * Copyright (C) 2026 Garudex Labs. All Rights Reserved.
 * Caracal, a product of Garudex Labs
 *
 * SDK Transport Adapter — base class and data structures.
 */

/** Outbound SDK request representation. */
export interface SDKRequest {
  method: string;
  path: string;
  headers: Record<string, string>;
  body?: Record<string, unknown>;
  params?: Record<string, unknown>;
}

/** Inbound SDK response representation. */
export interface SDKResponse {
  statusCode: number;
  headers: Record<string, string>;
  body: unknown;
  elapsedMs: number;
}

/** Abstract base for all transport adapters. */
export abstract class BaseAdapter {
  abstract send(request: SDKRequest): Promise<SDKResponse>;
  abstract close(): void;
  abstract get isConnected(): boolean;
}
