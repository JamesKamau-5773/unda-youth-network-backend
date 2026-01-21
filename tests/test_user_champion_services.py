import types
import pytest

from services import user_service, champion_service


class DummySession:
    def __init__(self):
        self._added = []

    def add(self, obj):
        self._added.append(obj)

    def flush(self):
        # assign simple incremental ids for added objects
        for idx, obj in enumerate(self._added, start=1):
            if hasattr(obj, 'username') and not getattr(obj, 'user_id', None):
                obj.user_id = idx
            if hasattr(obj, 'full_name') and not getattr(obj, 'champion_id', None):
                obj.champion_id = idx

    def commit(self):
        return None

    def rollback(self):
        return None


class FakeDB:
    def __init__(self):
        self.session = DummySession()


class FakeUser:
    # role constants used by services
    ROLE_PREVENTION_ADVOCATE = 'Prevention Advocate'
    ROLE_SUPERVISOR = 'Supervisor'

    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)
        self.failed_login_attempts = 0
        self.champion_id = None

    def set_invite(self, token, expires_at):
        self.invite_token = token
        self.invite_expires = expires_at

    def set_role(self, role_raw):
        # naive mapping for tests
        self.role = role_raw


class FakeChampion:
    query = types.SimpleNamespace(count=lambda: 0)

    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)
        self.champion_id = kwargs.get('champion_id', 1)


def test_create_user_sends_invite_when_email(monkeypatch):
    fake_db = FakeDB()
    monkeypatch.setattr(user_service, 'db', fake_db)
    monkeypatch.setattr(user_service, 'User', FakeUser)

    called = {}

    def fake_send_invite(email, username, token, expires_at):
        called['args'] = (email, username, token, expires_at)
        return True

    monkeypatch.setattr(user_service, 'send_invite', fake_send_invite)

    res = user_service.create_user('alice', 'alice@example.com', 'Supervisor')

    assert res['invite_sent'] is True
    assert 'invite_token' in res
    assert called.get('args') is not None


def test_create_champion_generates_code_and_sends_invite(monkeypatch):
    fake_db = FakeDB()
    monkeypatch.setattr(champion_service, 'db', fake_db)
    monkeypatch.setattr(champion_service, 'User', FakeUser)
    monkeypatch.setattr(champion_service, 'Champion', FakeChampion)

    called = {}

    def fake_send_invite(email, username, token, expires_at):
        called['args'] = (email, username, token, expires_at)
        return True

    monkeypatch.setattr(champion_service, 'send_invite', fake_send_invite)

    res = champion_service.create_champion('bob', 'Bob Example', 'bob@example.com', '0712345678', None)

    assert res['invite_sent'] is True
    assert 'champion_code' in res
    assert called.get('args') is not None
