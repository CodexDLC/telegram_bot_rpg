# RBC Version Changelog

## v3.1 (WIP - Target: Q2 2025)
### Added
- **Intent System:** Replacing raw `action_type` with structured Intent Objects.
- **Zone Auto-Resolution:** Zones are now semantic properties of Feints, not user input.
- **Token Economy:** Added 7+ types of tactical tokens (Hit, Block, Tempo, etc.).
- **Trigger System:** Separation of concerns between Pipeline Builder, Ability Service, and Calculator.

### Changed
- **ExchangePayload:** Structure updated to support new token types.
- **AI Ghost Agent:** Removed zone guessing, added token-based random selection.

### Deprecated
- Manual zone selection in client (Head/Legs buttons).

## v3.0 (Current - Released: Q4 2024)
### Added
- **Double Signaling:** Immediate + Timeout mechanism for robust turn handling.
- **Collector/Executor:** Separation of input collection and logic execution.
- **Dirty Flags:** Optimization for Redis writes.

### Removed
- Old `TurnOrchestrator` (merged into Gateway/Router).

## v2.0 (Legacy)
- Monolithic combat logic.
- Direct database access from logic.
