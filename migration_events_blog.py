"""
Migration script to add Event and BlogPost tables.
Run this on production after deploying the code changes.
"""

# This is a manual migration guide since we can't run flask db migrate locally

MIGRATION_SQL = """
-- Create events table
CREATE TABLE IF NOT EXISTS events (
    event_id SERIAL PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    event_date TIMESTAMP NOT NULL,
    location VARCHAR(255),
    event_type VARCHAR(100),
    organizer VARCHAR(255),
    max_participants INTEGER,
    registration_deadline TIMESTAMP,
    status VARCHAR(50) DEFAULT 'Upcoming',
    image_url VARCHAR(500),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by INTEGER REFERENCES users(user_id) ON DELETE SET NULL
);

-- Create blog_posts table
CREATE TABLE IF NOT EXISTS blog_posts (
    post_id SERIAL PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    slug VARCHAR(255) UNIQUE NOT NULL,
    content TEXT NOT NULL,
    excerpt TEXT,
    author_id INTEGER REFERENCES users(user_id) ON DELETE SET NULL,
    category VARCHAR(100),
    tags JSON,
    featured_image VARCHAR(500),
    published BOOLEAN DEFAULT FALSE,
    published_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    views INTEGER DEFAULT 0
);

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_events_date ON events(event_date);
CREATE INDEX IF NOT EXISTS idx_events_status ON events(status);
CREATE INDEX IF NOT EXISTS idx_blog_slug ON blog_posts(slug);
CREATE INDEX IF NOT EXISTS idx_blog_published ON blog_posts(published);
CREATE INDEX IF NOT EXISTS idx_blog_category ON blog_posts(category);

-- Add comments for documentation
COMMENT ON TABLE events IS 'Events and activities for the UNDA Youth Network';
COMMENT ON TABLE blog_posts IS 'Blog posts and articles for the UNDA Youth Network';
"""

print("=" * 80)
print("DATABASE MIGRATION SCRIPT")
print("=" * 80)
print("\nThis migration adds two new tables:")
print("  1. events - For managing events and activities")
print("  2. blog_posts - For managing blog content")
print("\nTo apply this migration on production:")
print("  1. Connect to your PostgreSQL database")
print("  2. Run the SQL commands below")
print("=" * 80)
print("\nSQL COMMANDS:")
print("=" * 80)
print(MIGRATION_SQL)
print("=" * 80)
print("\nAlternatively, Flask-Migrate will auto-detect these models")
print("when you run: flask db migrate")
print("=" * 80)
