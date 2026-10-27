from django.conf import settings
from django.core.checks import Warning, register


@register("mailer", deploy=True)
def brevo_key(app_configs, **kwargs):
    """
    Production needs a Brevo API key, or xikomu can't send any email (verification codes,
    murindzi alerts, password resets). build.sh runs check --deploy --fail-level WARNING, so a
    deploy without the key stops here instead of going live unable to send.
    """
    if settings.DEBUG or settings.BREVO_API_KEY:
        return []
    return [
        Warning(
            "BREVO_API_KEY isn't set, so xikomu can't send email.",
            hint=(
                "Create an API key in Brevo (SMTP & API, API keys) and add it to the "
                "environment as BREVO_API_KEY."
            ),
            id="mailer.W001",
        )
    ]
