"""SnapBack API entrypoint."""

from apps.api.app_factory import create_app
from apps.api.routes import health as health_routes

app = create_app()
root_redirect = health_routes.root_redirect
health_check = health_routes.health_check

__all__ = ["app", "root_redirect", "health_check"]
