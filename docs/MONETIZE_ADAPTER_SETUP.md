# Monetize Statistics integration: implementation and verification

The read-only adapter is in `src/integrations/vedoy-monetize.ts`. It does not emit telemetry, store visitor identifiers or create a second statistics backend.

## Before activation
1. Identify the **actual** Vedoy Monetize Statistics endpoint and its source repository. The Developer Portal README currently documents an API but does not establish the proposed Statistics summary endpoint.
2. Implement/verify the Monetize endpoint, project ownership, server-to-server scope, consent gating and response contract.
3. Configure the exact HTTPS origin in `allowedOrigins` and pass the token only from a server-side secret manager. Do not allow the browser to choose the origin.
4. Use `getMonetizeSummary(config, projectId, from, to)` from a trusted server, after authorizing the caller's project. Never expose the token.
5. A null return means no verified statistics are available. Show **Unavailable**, never zero.
6. Add contract tests against staging, enforce data minimization, aggregation thresholds, and avoid personal data in responses.

This is an integration boundary, not a claim that Monetize is already connected or that statistics are being collected.
