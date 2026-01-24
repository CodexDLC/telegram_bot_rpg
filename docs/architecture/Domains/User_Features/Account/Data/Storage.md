# Storage (Database & Redis)

[← Back to Data](./README.md)

## Database Tables (PostgreSQL)

### `users`
| Column | Type | Description |
|--------|------|-------------|
| `telegram_id` | BIGINT (PK) | Telegram User ID |
| `username` | VARCHAR(32) | @username |
| `first_name` | VARCHAR(64) | |
| `last_name` | VARCHAR(64) | |
| `is_premium` | BOOLEAN | |
| `created_at` | TIMESTAMP | |

### `characters`
| Column | Type | Description |
|--------|------|-------------|
| `char_id` | SERIAL (PK) | Character ID |
| `user_id` | BIGINT (FK) | Owner |
| `name` | VARCHAR(32) | Nullable (in onboarding) |
| `gender` | VARCHAR(10) | Nullable |
| `game_stage` | VARCHAR(20) | onboarding/tutorial/in_game |
| `vitals_snapshot` | JSONB | HP/MP/Stamina snapshot |
| `active_sessions` | JSONB | Active session IDs |

---

## Redis Structures

### Active Context (`ac:{char_id}`)
**Type:** RedisJSON
**TTL:** Permanent

```json
{
  "state": "string (Required) - CoreDomain enum",
  "location": {
    "current": "string (Required)",
    "prev": "string"
  },
  "bio": {
    "name": "string",
    "gender": "string",
    "created_at": "string"
  },
  "sessions": {
    "combat_id": "string",
    "inventory_id": "string"
  }
}
```

### Lobby Session Cache (`lobby:user:{user_id}`)
**Type:** String (JSON List)
**TTL:** 3600s
**Content:** List of `CharacterReadDTO`
