from django.apps import AppConfig


class MailerConfig(AppConfig):
    name = "mailer"
    verbose_name = "email"

    def ready(self):
        # The deploy check: production must have a Brevo API key (checks.py).
        from . import checks  # noqa: F401
