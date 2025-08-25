from django.apps import AppConfig

class ApiConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'api'

    def ready(self):
        """
        This method is called when the Django application is ready.
        We'll use it to train our ML models on startup if they don't exist.
        """
        # Import utils here to avoid AppRegistryNotReady error
        from . import utils
        import os

        # We only want this to run once, not every time the server reloads.
        # The run_main check ensures it runs only in the main Django process.
        if os.environ.get('RUN_MAIN', None) != 'true':
            print("Checking for ML models...")
            utils.train_and_save_models()

