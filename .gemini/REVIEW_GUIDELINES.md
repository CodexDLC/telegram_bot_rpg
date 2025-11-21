# Gemini Code Review Guidelines for Telegram Bot RPG

## Core Principles
This project follows **Clean Architecture** and **Data-Driven Design**. Focus on logic errors, security, and type safety.

### 1. Architecture & Data Consistency
* **Items & Inventory:** The project uses a "Pure Instance" model. Ensure that item data (stats, name, bonuses) is stored within the `item_data` JSON field of the `inventory_items` table.
    * *Flag as error:* Creating new tables for specific item types (e.g., `weapons` table).
    * *Flag as error:* Hardcoding item logic inside database models instead of using configuration files or services.
* **State Management:** Character modifiers are calculated dynamically. Ensure no attempts are made to persist calculated stats (like total HP or current damage) back into the database. Only base stats and raw item data should be persisted.

### 2. Python & Database Best Practices
* **Asynchronous Context:** Ensure all database operations use `AsyncSession`. Flag any synchronous DB calls or blocking I/O operations.
* **SQLAlchemy Usage:**
    * Check for proper use of `await session.flush()` when an ID is needed immediately after insertion.
    * Ensure `JSON` fields are handled correctly (passed as dictionaries).
* **Type Safety:** Strict typing is required. Ensure `TypeAdapter` is used for validating polymorphic Pydantic models (like `InventoryItemDTO`).

### 3. Code Quality & Security
* **Logging:** Use `loguru` for all logging. Flag any use of `print()`.
* **Hardcoding:** Text strings meant for users should be in `resources/texts/`, not in business logic.
* **Logic Gaps:** Look for edge cases in business logic (e.g., negative values in economy transactions, item duplication during transfers, missing validation).