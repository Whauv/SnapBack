"""SnapBack API entrypoint."""

from apps.api.app_factory import create_app
from apps.api.routes.health import health_check, root_redirect

app = create_app()
