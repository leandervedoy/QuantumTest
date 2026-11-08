# Vedoy Monetize integration contract for QuantumTest and Shield

**Decision:** Vedoy Monetize is the sole integration surface for optional product analytics. Its Statistics module owns consent and analytics; QuantumTest and Shield consume only authorized aggregated metrics through Monetize. Do not build a duplicate Statistics service inside QuantumTest.

## Architecture
- QuantumTest: scanner and evidence producer (TLS, PQC readiness, passive security, optional functional tests).
- Shield: schedule, subscription, job status, report history and alerts.
- Vedoy Monetize: consent UI/records, Statistics event ingestion and aggregation, data-access policies, optional Rewards and Advertize modules.
- No dependency on enabling advertising or rewards to access optional Statistics. Monetize must expose modules independently.
- Stripe: Shield billing remains in Shield's trusted backend; any future Monetize revenue analytics may receive only scoped aggregates, not payment secrets.

## API contract (proposed; verify against real Monetize code before wiring)
GET /v1/statistics/projects/{projectId}/summary?from=YYYY-MM-DD&to=YYYY-MM-DD
Response: { source: 'vedoy-monetize', from, to, consentScope, coverage, metrics: { pageViews?, conversions?, conversionRate?, revenueNok? }, generatedAt }
All fields optional when not measured. Never synthesize absent fields.
Auth: server-to-server short-lived scoped credentials; project ownership authorization; no cross-tenant reads.
Error behavior: unavailable Monetize -> technical report still succeeds; analytics shown as unavailable.

## Privacy
- Optional tracking disabled by default; respect Monetize's recorded choices and withdrawal.
- No visitor IDs, IP addresses, free-text payloads or event logs copied into QuantumTest.
- Aggregation must prevent reidentification; small cohorts suppressed.
- No persistent telemetry in no-storage mode. Historical aggregates are storage, even if anonymous.
- Existing Monetize data practices require verification for GDPR/ePrivacy; the presence of a consent popup alone does not prove compliance.

## Report
Technical observations, Monetize-measured metrics, modelled revenue scenarios and AI-simulated persona feedback must have separate labels and provenance.
Never infer conversion improvement causally from a scan alone.

## Integration status
Design-only: no Monetize repository/API endpoint was verified in this change. Do not claim live data sync.
Next: locate actual Monetize module in Developer Portal or its own repository; inspect auth, API and consent model; implement contract tests and scoped server adapter; then stage and verify.
