from __future__ import annotations

from backend.app import create_app


def test_create_app_registers_core_api_routes() -> None:
    app = create_app()
    route_paths = {
        route.path
        for route in app.routes
    }

    assert "/" in route_paths
    assert "/healthz" in route_paths
    assert "/api/meetings/import" in route_paths
    assert "/api/meetings/{meeting_id}/review" in route_paths
    assert "/api/deliverables/generate" in route_paths
    assert "/api/projects/{project_id}/memory" in route_paths
    assert "/api/projects/{project_id}/action-items/status" in route_paths
