import os
import sys
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from models import db, BlogPost
from services import story_service


@pytest.fixture
def app():
    test_config = {
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "WTF_CSRF_ENABLED": False,
        "RATELIMIT_STORAGE_URL": "memory://",
    }
    app, limiter = create_app(test_config=test_config)

    with app.app_context():
        db.create_all()
        yield app


def test_create_story_success(app):
    data = {'title': 'My Story', 'content': 'Once upon', 'excerpt': 'Short', 'featured_image': None}
    with app.app_context():
        p = story_service.create_story(data, author_id=1, publish=True)
        assert p.post_id is not None
        assert p.title == 'My Story'
        assert p.published is True


def test_create_story_requires_title_and_content(app):
    data = {'title': '', 'content': ''}
    with app.app_context():
        with pytest.raises(ValueError):
            story_service.create_story(data, author_id=1)


def test_update_story(app):
    with app.app_context():
        p = BlogPost(title='Old', slug='old', content='c', author_id=1)
        db.session.add(p)
        db.session.commit()
        data = {'title': 'New', 'content': 'Updated', 'excerpt': 'ex'}
        updated = story_service.update_story(p.post_id, data)
        assert updated.title == 'New'
        assert updated.content == 'Updated'


def test_delete_story(app):
    with app.app_context():
        p = BlogPost(title='To delete', slug='del', content='c', author_id=1)
        db.session.add(p)
        db.session.commit()
        story_service.delete_story(p.post_id)
        assert db.session.get(BlogPost, p.post_id) is None
