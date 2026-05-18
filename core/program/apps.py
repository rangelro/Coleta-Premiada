from django.apps import AppConfig


class ProgramConfig(AppConfig):
    name = 'program'

    def ready(self):
        import program.signals  # noqa: F401 — conecta os signals ao iniciar o app
