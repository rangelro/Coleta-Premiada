from django.apps import AppConfig


class CollectionConfig(AppConfig):
    name = 'collection'

    def ready(self):
        import collection.signals  # noqa: F401
