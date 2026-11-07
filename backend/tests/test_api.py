from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


class TestApiEndpoints:
    def test_health_endpoint(self) -> None:
        """GET /health must return 200 with status 'healthy' and app metadata."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["app"] == "AttendPlan"
        assert "version" in data
        assert "timestamp" in data

    def test_sample_attendance_endpoint(self) -> None:
        """GET /api/v1/attendance/sample must return 200 with 15 courses and SAMPLE provenance."""
        response = client.get("/api/v1/attendance/sample")
        assert response.status_code == 200
        data = response.json()

        assert data["id"] == "snap-sample-fall-2026"
        assert data["provenance"] == "SAMPLE_HISTORICAL"
        assert data["provenance_label"] == "SAMPLE / HISTORICAL FIXTURE"
        assert data["academic_year"] == "2026-2027"
        assert data["semester"] == 5
        assert len(data["courses"]) == 15

        # Summary assertions
        summary = data["summary"]
        assert summary["total_courses"] == 15
        assert summary["total_attended"] == 185
        assert summary["total_delivered"] == 213
        assert summary["overall_percentage"] == 86.85
        assert summary["overall_status"] == "SAFE"

        # Check course structure
        first = data["courses"][0]
        assert "code" in first
        assert "name" in first
        assert "attended" in first
        assert "delivered" in first
        assert "percent" in first
        assert "status" in first

    def test_sample_attendance_with_custom_target(self) -> None:
        """GET /api/v1/attendance/sample?target=80.0 recalculates margins for 80%."""
        response = client.get("/api/v1/attendance/sample?target=80.0")
        assert response.status_code == 200
        data = response.json()
        assert data["target_percentage"] == 80.0

        # In 80% target, CSH310C (15/20 = 75%) becomes AT_RISK instead of SAFE!
        csh310 = next(c for c in data["courses"] if c["code"] == "CSH310C")
        assert csh310["status"] == "AT_RISK"
        assert csh310["must_attend"] > 0

    def test_simulation_endpoint(self) -> None:
        """POST /api/v1/simulation/simulate simulates lecture deltas."""
        payload = {
            "target_percentage": 75.0,
            "courses": [
                {
                    "code": "CSH311C",
                    "attended": 10,
                    "delivered": 14,
                    "delta_attended": 2,
                    "delta_missed": 0,
                },
                {
                    "code": "CSH302C",
                    "attended": 19,
                    "delivered": 19,
                    "delta_attended": 0,
                    "delta_missed": 6,
                },
            ],
        }
        response = client.post("/api/v1/simulation/simulate", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert len(data["results"]) == 2

        # CSH311C: was 10/14 (71.43%, AT_RISK), with +2 attended -> 12/16 (75.0%, SAFE)
        res1 = data["results"][0]
        assert res1["code"] == "CSH311C"
        assert res1["original_status"] == "AT_RISK"
        assert res1["simulated_status"] == "SAFE"
        assert res1["simulated_percent"] == 75.0
        assert res1["status_changed"] is True

        # CSH302C: was 19/19 (100%), with +6 missed -> 19/25 (76.0%, SAFE)
        res2 = data["results"][1]
        assert res2["code"] == "CSH302C"
        assert res2["simulated_status"] == "SAFE"

    def test_verified_route_inventory(self) -> None:
        """Automatically verify and audit exact FastAPI route inventory."""
        expected_endpoints = {
            ("POST", "/api/v1/attendance-archive/resume"),
            ("POST", "/api/v1/attendance-archive/plan"),
            ("POST", "/api/v1/attendance-archive/start"),
            ("GET", "/api/v1/attendance-archive/status"),
            ("POST", "/api/v1/attendance-archive/cancel"),
            ("GET", "/api/v1/attendance-archive/calendars"),
            ("GET", "/api/v1/attendance-archive/calendars/{term_key}"),
            ("POST", "/api/v1/attendance-archive/calendars/{term_key}"),
            ("POST", "/api/v1/attendance-archive/calendars/{term_key}/reset"),
            ("POST", "/api/v1/terms/{term_id}/attendance/month-preview"),
            ("GET", "/api/v1/terms/{term_id}/attendance/periods"),
            ("POST", "/api/v1/performance/discover-scopes"),
            ("GET", "/api/v1/startup/settings"),
            ("POST", "/api/v1/startup/settings"),
            ("GET", "/api/v1/startup/status"),
            ("POST", "/api/v1/startup/connect"),
            ("POST", "/api/v1/startup/refresh-current"),
            ("GET", "/api/v1/performance/overview"),
            ("POST", "/api/v1/performance/preview"),
            ("POST", "/api/v1/performance/import"),
            ("GET", "/api/v1/performance/official-results"),
            ("GET", "/health"),
            ("GET", "/api/v1/attendance/sample"),
            ("POST", "/api/v1/demo/seed"),
            ("POST", "/api/v1/simulation/simulate"),
            ("GET", "/api/v1/terms"),
            ("GET", "/api/v1/terms/{term_id}/attendance"),
            ("GET", "/api/v1/terms/{term_id}/snapshots"),
            ("GET", "/api/v1/terms/{term_id}/analytics/summary"),
            ("GET", "/api/v1/terms/{term_id}/analytics/monthly"),
            ("GET", "/api/v1/terms/{term_id}/analytics/weekday"),
            ("GET", "/api/v1/terms/{term_id}/analytics/daily"),
            ("GET", "/api/v1/terms/{term_id}/analytics/subjects"),
            ("GET", "/api/v1/terms/{term_id}/analytics/calendar"),
            ("GET", "/api/v1/analytics/academic-history"),
            ("GET", "/api/v1/terms/{term_id}/reconciliation"),
            ("POST", "/api/v1/attendance/imports/html"),
            ("GET", "/api/v1/attendance/ingestions"),
            ("GET", "/api/v1/portal/session/status"),
            ("POST", "/api/v1/portal/session/launch"),
            ("POST", "/api/v1/portal/session/close"),
            ("POST", "/api/v1/portal/session/disconnect"),
            ("POST", "/api/v1/portal/discover/terms"),
            ("POST", "/api/v1/portal/discover/subject-wise"),
            ("POST", "/api/v1/portal/discover/day-wise"),
            ("POST", "/api/v1/portal/discover/overall"),
            ("POST", "/api/v1/portal/sync/subject-wise"),
            ("POST", "/api/v1/portal/sync/day-wise"),
            ("POST", "/api/v1/portal/sync/pilot"),
            ("GET", "/api/v1/portal/sync/historical-plan"),
            ("GET", "/api/v1/portal/sync/jobs/latest"),
            ("GET", "/api/v1/portal/sync/jobs/{job_id}"),
            ("POST", "/api/v1/portal/sync/jobs/{job_id}/cancel"),

            ("GET", "/api/v1/auth/settings"),
            ("POST", "/api/v1/auth/settings"),
            ("GET", "/api/v1/auth/totp/status"),
            ("POST", "/api/v1/auth/totp/inspect"),
            ("POST", "/api/v1/auth/totp/enroll"),
            ("POST", "/api/v1/auth/totp/enroll-image"),
            ("POST", "/api/v1/auth/totp/verify"),
            ("DELETE", "/api/v1/auth/totp/enrollment"),
            ("PATCH", "/api/v1/auth/totp/settings"),
            ("POST", "/api/v1/auth/totp/autofill"),
            ("POST", "/api/v1/auth/login/orchestrate"),
            ("GET", "/api/v1/auth/login/status"),
            ("POST", "/api/v1/auth/backup/export"),

            # F2-E Historical Multi-Semester Endpoints
            ("GET", "/api/v1/historical/terms"),
            ("POST", "/api/v1/historical/discover"),
            ("POST", "/api/v1/historical/preview"),
            ("POST", "/api/v1/historical/import"),
            ("GET", "/api/v1/historical/import/progress"),
            ("POST", "/api/v1/historical/import/cancel"),
            ("GET", "/api/v1/historical/overview"),
            ("GET", "/api/v1/terms/{term_id}/coverage"),
        }

        # Filter out auto-generated docs / openapi routes
        app_routes = set()
        for r in app.routes:
            if isinstance(r, APIRoute) and not r.path.startswith("/docs") and not r.path.startswith("/redoc") and r.path != "/openapi.json":
                for m in r.methods:
                    if m != "HEAD":
                        app_routes.add((m, r.path))

        assert app_routes == expected_endpoints
        assert len(app_routes) == 74




