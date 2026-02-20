/**
 * Copyright (C) 2026 Garudex Labs. All Rights Reserved.
 * Caracal, a product of Garudex Labs
 *
 * SDK Agent Operations.
 */

import { SDKRequest } from './adapters/base';
import { ScopeContext } from './context';

export class AgentOperations {
  constructor(private readonly scope: ScopeContext) {}

  private buildReq(method: string, path: string, body?: Record<string, unknown>, params?: Record<string, unknown>): SDKRequest {
    return { method, path, headers: { ...this.scope.scopeHeaders() }, body, params };
  }

  private async exec(req: SDKRequest): Promise<unknown> {
    const scoped = await this.scope._hooks.fireBeforeRequest(req, this.scope.toScopeRef());
    try {
      const res = await this.scope._adapter.send(scoped);
      this.scope._hooks.fireAfterResponse(res, this.scope.toScopeRef());
      return res.body;
    } catch (e) {
      this.scope._hooks.fireError(e as Error);
      throw e;
    }
  }

  async list(options?: { limit?: number; offset?: number }): Promise<unknown> {
    return this.exec(this.buildReq('GET', '/agents', undefined, { limit: options?.limit ?? 100, offset: options?.offset ?? 0 }));
  }

  async get(agentId: string): Promise<unknown> {
    return this.exec(this.buildReq('GET', `/agents/${agentId}`));
  }

  async create(options: { name: string; owner: string; metadata?: Record<string, unknown> }): Promise<unknown> {
    const body: Record<string, unknown> = { name: options.name, owner: options.owner };
    if (options.metadata) body.metadata = options.metadata;
    return this.exec(this.buildReq('POST', '/agents', body));
  }

  async update(agentId: string, data: Record<string, unknown>): Promise<unknown> {
    return this.exec(this.buildReq('PATCH', `/agents/${agentId}`, data));
  }

  async delete(agentId: string): Promise<unknown> {
    return this.exec(this.buildReq('DELETE', `/agents/${agentId}`));
  }

  async createChild(options: { parentAgentId: string; childName: string; childOwner: string; generateToken?: boolean }): Promise<unknown> {
    return this.exec(this.buildReq('POST', `/agents/${options.parentAgentId}/children`, {
      child_name: options.childName,
      child_owner: options.childOwner,
      generate_token: options.generateToken ?? false,
    }));
  }
}
