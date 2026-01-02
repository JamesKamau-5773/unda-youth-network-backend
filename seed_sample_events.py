"""
Create non-destructive sample events for each category to verify Events API.
Run: python seed_sample_events.py
"""
from datetime import datetime, timedelta

from app import create_app
from models import db, Event, User


SAMPLE_EVENTS = [
    {
        "title": "Debaters Circle: Youth Mental Health",
        "description": "Structured debate on resilience, stigma reduction, and peer support.",
        "event_type": "debate",
        "location": "Nairobi Hub",
        "organizer": "UNDA Program Team",
        "offset_days": 7,
    },
    {
        "title": "UMV Mtaani Baraza: Community Listening",
        "description": "Community dialogue with local leaders and youth mentors.",
        "event_type": "mtaani",
        "location": "Kisumu East Community Centre",
        "organizer": "County Youth Office",
        "offset_days": 14,
    },
    {
        "title": "Podcast Live Recording: Healing Stories",
        "description": "Live audience recording featuring champion-led success stories.",
        "event_type": "podcast",
        "location": "Studio A",
        "organizer": "UNDA Media",
        "offset_days": 1,
    },
]


def seed_events():
    app = create_app()
    with app.app_context():
        admin_user = User.query.filter_by(role="Admin").first()
        now = datetime.utcnow()

        created = []
        skipped = []

        for payload in SAMPLE_EVENTS:
            existing = Event.query.filter_by(title=payload["title"]).first()
            if existing:
                skipped.append((payload["title"], existing.event_id))
                continue

            event_date = now + timedelta(days=payload["offset_days"])
            registration_deadline = event_date - timedelta(days=1)

            event = Event(
                title=payload["title"],
                description=payload["description"],
                event_date=event_date,
                location=payload["location"],
                event_type=payload["event_type"],
                organizer=payload["organizer"],
                max_participants=100,
                registration_deadline=registration_deadline,
                status="Upcoming",
                created_by=admin_user.user_id if admin_user else None,
            )
            db.session.add(event)
            created.append(payload["title"])

        if created:
            db.session.commit()

        print("Seed events summary:")
        print(f"  Created: {created if created else 'None'}")
        print(f"  Skipped (already existed): {skipped if skipped else 'None'}")


if __name__ == "__main__":
    seed_events()
