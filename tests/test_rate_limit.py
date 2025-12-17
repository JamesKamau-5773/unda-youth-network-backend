import unittest
import sys
import os

# Ensure we can import from the parent directory
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db

class RateLimitTestCase(unittest.TestCase):
    def setUp(self):
        # Configure app for testing with in-memory storage for rate limiter
        # This ensures we don't need a running Redis instance for tests
        test_config = {
            'TESTING': True,
            'RATELIMIT_ENABLED': True,
            'RATELIMIT_STORAGE_URL': 'memory://',
            'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
            'WTF_CSRF_ENABLED': False
        }
        self.app, self.limiter = create_app(test_config)
        self.client = self.app.test_client()
        
        # Create app context
        self.ctx = self.app.app_context()
        self.ctx.push()
        
        # Ensure database tables exist (create_app does this, but good to be explicit in setup)
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def test_login_rate_limit_flow(self):
        """
        Verifies TC 3.1, 3.2, and 3.3 for Rate Limiting.
        
        Note: TC 3.2 explicitly states "Attempt 5 is Blocked".
        This implies a limit of 4 allowed requests per minute.
        The test verifies the "4 per minute" behavior implemented in auth.py.
        """
        login_url = '/auth/login'
        credentials = {'username': 'testuser', 'password': 'wrongpassword'}

        # TC 3.1: Normal Attempts
        # Attempts 1-4 should succeed (return 200 OK with error message, not 429)
        for i in range(4):
            response = self.client.post(login_url, data=credentials)
            self.assertNotEqual(
                response.status_code, 429, 
                f"TC 3.1 Failed: Attempt {i+1} was rate limited prematurely."
            )

        # TC 3.2: Rate Limit Trigger
        # Attempt 5 should be blocked
        response = self.client.post(login_url, data=credentials)
        self.assertEqual(
            response.status_code, 429, 
            "TC 3.2 Failed: Rate limit was not triggered on the 5th attempt."
        )
        self.assertIn(b"Too Many Requests", response.data)

        # TC 3.3: Limit Reset
        # Reset the limiter storage to simulate time passing
        if hasattr(self.limiter, 'storage') and hasattr(self.limiter.storage, 'reset'):
            self.limiter.storage.reset()
        
        response = self.client.post(login_url, data=credentials)
        self.assertNotEqual(
            response.status_code, 429, 
            "TC 3.3 Failed: Rate limit did not reset after clearing."
        )

if __name__ == '__main__':
    unittest.main()