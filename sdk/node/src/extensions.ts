/**
 * Copyright (C) 2026 Garudex Labs. All Rights Reserved.
 * Caracal, a product of Garudex Labs
 *
 * SDK Extension interface.
 */

import { HookRegistry } from './hooks';

/** Base interface for all Caracal SDK extensions (open-source and enterprise). */
export interface CaracalExtension {
  readonly name: string;
  readonly version: string;

  /**
   * Register callbacks on lifecycle hooks.
   * Called exactly once when the extension is attached via `.use()`.
   */
  install(hooks: HookRegistry): void;
}
