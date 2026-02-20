/**
 * Copyright (C) 2026 Garudex Labs. All Rights Reserved.
 * Caracal, a product of Garudex Labs
 *
 * HTTP/REST transport adapter (default).
 */

import { BaseAdapter, SDKRequest, SDKResponse } from './base';

export class HttpAdapter extends BaseAdapter {
  private readonly baseUrl: string;
  private readonly apiKey?: string;
  private readonly timeout: number;
  private readonly maxRetries: number;
  private connected = false;

  constructor(options: {
    baseUrl: string;
    apiKey?: string;
    timeout?: number;
    maxRetries?: number;
  }) {
    super();
    this.baseUrl = options.baseUrl.replace(/\/+$/, '');
    this.apiKey = options.apiKey;
    this.timeout = options.timeout ?? 30_000;
    this.maxRetries = options.maxRetries ?? 3;
    this.connected = true;
  }

  async send(request: SDKRequest): Promise<SDKResponse> {
    const url = new URL(request.path, this.baseUrl);
    if (request.params) {
      for (const [k, v] of Object.entries(request.params)) {
        url.searchParams.set(k, String(v));
      }
    }

    const headers: Record<string, string> = { ...request.headers };
    if (this.apiKey) {
      headers['Authorization'] = `Bearer ${this.apiKey}`;
    }
    if (request.body) {
      headers['Content-Type'] = 'application/json';
    }

    const start = performance.now();

    const resp = await fetch(url.toString(), {
      method: request.method,
      headers,
      body: request.body ? JSON.stringify(request.body) : undefined,
      signal: AbortSignal.timeout(this.timeout),
    });

    const elapsed = performance.now() - start;
    const body = resp.headers.get('content-type')?.includes('json')
      ? await resp.json()
      : await resp.text();

    return {
      statusCode: resp.status,
      headers: Object.fromEntries(resp.headers.entries()),
      body,
      elapsedMs: Math.round(elapsed * 100) / 100,
    };
  }

  close(): void {
    this.connected = false;
  }

  get isConnected(): boolean {
    return this.connected;
  }
}
