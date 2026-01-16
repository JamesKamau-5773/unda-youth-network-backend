from celery import Celery
import os

def make_celery(app=None):
    # Lazily create Celery with Flask config if available
    broker = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
    backend = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
    celery = Celery('unda', broker=broker, backend=backend)
    if app:
        celery.conf.update(app.config)

        class ContextTask(celery.Task):
            def __call__(self, *args, **kwargs):
                with app.app_context():
                    return self.run(*args, **kwargs)

        celery.Task = ContextTask
    return celery
