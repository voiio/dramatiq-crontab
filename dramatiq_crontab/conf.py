from __future__ import annotations

from django.conf import settings


def get_settings():
    return type(
        "Settings",
        (),
        {
            "REDIS_URL": None,
            **getattr(settings, "DRAMATIQ_CRONTAB", {}),
        },
    )
