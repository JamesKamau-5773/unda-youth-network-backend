from app import create_app
from celery_app import make_celery

# Create Flask app and bind Celery to it so the worker has the same app context
app, _ = create_app()
celery = make_celery(app)

# Import tasks so they get registered with this Celery instance
import tasks.media_tasks  # noqa: F401
# If tasks were defined as plain functions (synchronous fallback) when the
# tasks module was first imported, ensure they are registered on this
# Celery instance so the worker recognizes them.
try:
	if hasattr(tasks.media_tasks, 'generate_and_store_thumbnail'):
		# Register the function as a Celery task under the expected name
		# If the module provided a synchronous fallback or a different celery
		# instance registered the task, ensure this Celery instance exposes
		# a task named 'tasks.generate_and_store_thumbnail' that runs the
		# underlying implementation inside the Flask app context.
		def _wrapper(gallery_id, media_path):
			with app.app_context():
				return tasks.media_tasks._generate_and_store_thumbnail(gallery_id, media_path)

		celery.task(name='tasks.generate_and_store_thumbnail')(_wrapper)
		tasks.media_tasks._registered_with_celery = True
except Exception:
	# Do not fail app import if registration fails; worker logs will show issues
	pass
