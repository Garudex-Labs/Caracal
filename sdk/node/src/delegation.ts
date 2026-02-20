/**
 * Copyright (C) 2026 Garudex Labs. All Rights Reserved.
 * Caracal, a product of Garudex Labs
 *
 * SDK Delegation Operations.
 */

import { SDKRequest } from './adapters/base';
import { ScopeContext } from './context';

export class DelegationOperations {
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

  async create(options: {
    parentMandateId: string;
    childSubjectId: string;
    resourceScope: string[];
    actionScope: string[];
    validitySeconds: number;
    metadata?: Record<string, unknown>;
  }): Promise<unknown> {
    const body: Record<string, unknown> = {
      parent_mandate_id: options.parentMandateId,
      child_subject_id: options.childSubjectId,
      resource_scope: options.resourceScope,
      action_scope: options.actionScope,
      validity_seconds: options.validitySeconds,
    };
    if (options.metadata) body.metadata = options.metadata;
    return this.exec(this.buildReq('POST', '/delegations', body));
  }

  async getToken(options: {
    parentAgentId: string;
    childAgentId: string;
    expirationSeconds?: number;
    allowedOperations?: string[];
  }): Promise<unknown> {
    const body: Record<string, unknown> = {
      parent_agent_id: options.parentAgentId,
      child_agent_id: options.childAgentId,
      expiration_seconds: options.expirationSeconds ?? 86400,
    };
    if (options.allowedOperations) body.allowed_operations = options.allowedOperations;
    return this.exec(this.buildReq('POST', '/delegations/token', body));
  }

  async getChain(agentId: string): Promise<unknown> {
    return this.exec(this.buildReq('GET', `/delegations/chain/${agentId}`));
  }
}
