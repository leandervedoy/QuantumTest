# Vedoy Shield monthly QuantumTest integration

Status: integration scaffold, **not deployed or production-ready**.

## Scope
Monthly passive TLS, post-quantum readiness, and security checks. PQC checks assess observable cryptographic configuration; they cannot certify quantum safety. No IBM hardware required.

## Billing
Suggested Shield Basic: NOK 99/month (not the NOK 300 one-time QuantumTest price). Create a recurring Stripe Price in NOK. Server creates Checkout Session using the authenticated owner, allowlisted price ID, and project ID. Never trust a client-supplied price or customer ID. On verified Stripe webhooks handle checkout.session.completed, customer.subscription.created/updated/deleted and invoice.payment_failed. Store event IDs for deduplication, check signature against raw request body, and map Stripe subscription status to shield_subscriptions. Activate scans only after verified active/trialing status AND explicit target authorization. Cancel/disable scans on canceled/unpaid subscription. Stripe secrets stay server-side.

## Scheduler and worker
Run scheduleDue with a trusted scheduled job; call claimJob through a service-role client; use runOne with an isolated adapter. Do not run scanning within the web request. Restrict network egress, block internal/loopback/link-local IPs including DNS rebinding, verify target ownership, rate-limit, limit concurrency, cap execution time, and use passive checks by default. Do not scan targets without authorization. Store only minimal scan evidence; redact secrets and PII.

## Production blockers
- Implement real Stripe Checkout and signed webhook endpoints with persistent event deduplication.
- Implement scan adapter (TLS, PQC readiness, passive ZAP) with SSRF protections and domain verification.
- Add an atomic scheduler reservation/advance RPC to eliminate races and avoid missed runs.
- Recover expired running-job leases and add retry/dead-letter monitoring.
- Build notification delivery (email or in-app), opt-out and deduplication.
- Add end-to-end tests for billing transitions, permissions, time boundaries, worker crashes, and webhook retries.
- Verify RLS, migrations and pricing in a staging environment before deployment.

Do not advertise this scaffold as a functioning subscription until all blockers are resolved.
