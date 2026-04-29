# Town Warden Network: Federation Roadmap

Town Warden is local-first today. Each town clone should work as a complete,
independent civic-intelligence node before any network features are considered.

This document describes a future "Town Warden Network" concept. It is a
roadmap, not an implemented feature. No federation endpoints, network calls, or
cross-town data sharing are active in v1.0.

Town Warden remains an experimental civic-tech prototype. It is not official
council, police, NHS, emergency-service, or public authority advice.

## 1. Local-First Design

Each Town Warden instance belongs to one town.

Examples:

- Blackpool Town Warden
- Preston Town Warden
- Manchester Town Warden
- Liverpool Town Warden

Each town keeps its own:

- town config
- source settings
- database
- dashboard
- civic-risk model
- agent insight history
- protected developer/admin routes

A town instance must work perfectly without federation. Federation should be an
optional layer on top of local civic intelligence, not a dependency.

## 2. Future Federation Idea

In a future version, town instances could publish public-safe summaries to
trusted peers or a federation hub.

The goal is cross-town pattern awareness, not centralised surveillance. Towns
should not share raw records by default. The network should move summaries,
confidence scores, and limitations, not private or operational data.

## 3. Safe Summary Example

```json
{
  "node_id": "blackpool",
  "town_name": "Blackpool",
  "period": "2026-04-29",
  "signal_type": "location_concentration",
  "severity": "watch",
  "confidence": 0.72,
  "summary": "Repeated public-source incident concentration detected in a local zone.",
  "source_mix": ["Police.uk", "Street Manager"],
  "public_safe": true
}
```

## 4. What Could Be Shared Later

Future federation should share only public-safe aggregate information, such as:

- aggregate insight summaries
- source status summaries
- risk trend summaries
- public-safe agent insight summaries
- town-level event category counts
- non-sensitive map/risk summaries

## 5. What Should Not Be Shared

Town Warden nodes should not share:

- admin tokens
- database URLs
- raw webhook payloads
- exact sensitive records
- private credentials
- personal data
- operational emergency data
- anything implying official police/council authority

## 6. Future Network Models

Possible network shapes:

- Peer-to-peer town nodes: trusted towns exchange signed public summaries.
- Regional hub: a North West hub receives read-only public-safe summaries from
  participating towns.
- National public-source index: aggregated public-source trend summaries from
  many local nodes.
- Read-only public summary API: each town exposes its own local public summary
  endpoint without accepting incoming peer writes.

## 7. Future Agent Communication Examples

Example future flow:

1. Blackpool Pattern Warden detects a South Shore concentration.
2. Preston Pattern Warden detects a similar transport-hub concentration.
3. Regional Pattern Warden notices similar patterns across several North West
   towns.
4. The regional agent publishes a cautious summary: similar public-source
   patterns are appearing across several towns, with confidence and limitations.

This should never become an emergency-response claim. It should remain a
source-limited early-warning aid for civic analysts and developers.

## 8. Ethics And Safety

Federation must preserve the project's safety posture:

- public-source only
- not official advice
- no emergency response claims
- local context matters
- confidence scoring is required
- source limitations must be visible
- avoid overclaiming
- avoid surveillance framing
- avoid raw data sharing by default

## 9. Possible Future Endpoints

These endpoints are suggestions only. They are not implemented yet.

```text
GET  /federation/node-profile
GET  /federation/public-summary
POST /federation/receive-summary
GET  /federation/peer-status
```

## 10. Possible Future Config

Future environment variables might include:

```text
FEDERATION_ENABLED=false
FEDERATION_NODE_ID=blackpool
FEDERATION_PUBLIC_URL=
FEDERATION_SHARED_SECRET=
FEDERATION_PEERS=
```

Federation should be disabled by default. Secrets must never be committed to the
repo or exposed in frontend code.

## 11. Future Implementation Phases

Suggested staged plan:

1. Documentation and schema.
2. Local public summary endpoint.
3. Signed node identity.
4. Trusted peer exchange.
5. Regional pattern agents.
6. Public federation dashboard.

Each phase should keep the local town instance usable on its own.
