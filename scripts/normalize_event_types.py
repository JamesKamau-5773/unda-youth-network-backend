"""Normalize Event.event_type values to required set.

Required event_type values:
- conference
- debate
- baraza
- international

Usage:
  # Dry run (default)
  python scripts/normalize_event_types.py

  # Apply changes
  python scripts/normalize_event_types.py --apply

  # Optional: use a specific DATABASE_URL
  DATABASE_URL=postgresql://... python scripts/normalize_event_types.py --apply
"""

import argparse
from collections import Counter

from app import create_app
from models import db, Event


TARGET_TYPES = {"conference", "debate", "baraza", "international"}

ALIASES = {
    "conference": {"conference", "annual conference", "umv annual conference", "umv conference"},
    "debate": {"debate", "debaters", "debaters circle", "debate event", "umv debaters"},
    "baraza": {"baraza", "barazas", "mtaani", "umv mtaani", "community baraza"},
    "international": {
        "international",
        "partnership",
        "partnerships",
        "international partnership",
        "international partnerships",
        "umv global",
        "global",
    },
}


def normalize_event_type(value: str) -> str:
    if not value:
        return value
    normalized = value.strip().lower()
    for target, aliases in ALIASES.items():
        if normalized in aliases:
            return target
    return normalized


def main() -> int:
    parser = argparse.ArgumentParser(description="Normalize event_type values.")
    parser.add_argument("--apply", action="store_true", help="Apply updates to the database")
    args = parser.parse_args()

    app, _ = create_app()
    with app.app_context():
        events = Event.query.all()

        original_types = Counter()
        normalized_types = Counter()
        updates = []

        for event in events:
            original = event.event_type or ""
            original_types[original or "(empty)"] += 1
            normalized = normalize_event_type(original)
            normalized_types[normalized or "(empty)"] += 1

            if normalized and original != normalized:
                updates.append((event.event_id, original, normalized))

        print("\nEvent type summary (current):")
        for k, v in original_types.most_common():
            print(f"  {k}: {v}")

        print("\nEvent type summary (normalized):")
        for k, v in normalized_types.most_common():
            print(f"  {k}: {v}")

        if not updates:
            print("\nNo updates required.")
            return 0

        print(f"\nPlanned updates: {len(updates)}")
        for event_id, original, normalized in updates[:20]:
            print(f"  Event {event_id}: {original} -> {normalized}")
        if len(updates) > 20:
            print(f"  ... and {len(updates) - 20} more")

        if not args.apply:
            print("\nDry run only. Re-run with --apply to write changes.")
            return 0

        # Apply updates
        for event_id, original, normalized in updates:
            event = Event.query.get(event_id)
            if event:
                event.event_type = normalized

        db.session.commit()
        print("\nUpdates applied successfully.")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
