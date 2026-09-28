# Integration Pack

## Folder 1
Use Reflex prompts in order:
00 -> 01 -> 02 -> 03 -> 04 -> 05 -> 06 -> 07

## Folder 2
Share the complete API contract and quick endpoint list with teammates.

Before coding in parallel, freeze:
- JSON field names
- status enums
- authentication
- tenant authorization
- async behavior
- error format
- pagination
- timestamp/ID conventions

JSON is transport; PostgreSQL is persistence; FastAPI is the integration boundary.
Current path: Reflex UI -> FastAPI -> PostgreSQL / New Relic / LangGraph / Notification.

Architecture and flow diagrams:
- See ARCHITECTURE_FLOW_DIAGRAM.md for the current implemented component view and end-to-end incident workflow.
