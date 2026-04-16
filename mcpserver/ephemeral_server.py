"""
Ephemeral btcopilot server for isolated e2e testing.

Spawned as a subprocess by the MCP test server. Provides a fully isolated
Flask + SQLite instance that can be seeded with test data on demand.

Usage:
    uv run --directory /path/to/theapp python -u \
        familydiagram/mcpserver/ephemeral_server.py \
        --port 5555 --db-dir /tmp/fd_test_xyz/db
"""

import argparse
import logging
import os
import pickle
import signal
import sys

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("ephemeral-server")


def _disable_heavy_extensions():
    """Noop extensions that aren't needed for e2e testing."""
    import btcopilot.extensions as ext

    ext.init_logging = lambda app: None
    ext.init_excepthook = lambda app: None
    ext.init_celery = lambda app: None
    ext.init_datadog = lambda app: None
    ext.init_stripe = lambda app: None
    ext.init_chroma = lambda app: None
    ext.init_mail = lambda app: None


def _mock_passwords():
    """Replace bcrypt password hashing with fast mock."""
    from btcopilot.pro.models import User

    def _set(self, plaintext):
        self.password = f"mock_hash:{plaintext}"
        self.reset_password_code = None

    def _check(self, plaintext):
        return self.password == f"mock_hash:{plaintext}"

    User.set_password = _set
    User.check_password = _check


def _register_test_routes(app):
    """Register test-only endpoints for data seeding and health checks."""
    from flask import jsonify, request

    import btcopilot
    from btcopilot.extensions import db
    from btcopilot.pro.models import (
        Activation,
        Diagram,
        License,
        Machine,
        Policy,
        User,
    )

    @app.route("/test/seed", methods=["POST"])
    def test_seed():
        data = request.get_json()
        result = {"success": True, "users": [], "diagrams": []}

        for ud in data.get("users", []):
            user = User(
                username=ud["username"],
                first_name=ud.get("first_name", "Test"),
                last_name=ud.get("last_name", "User"),
                status=ud.get("status", "confirmed"),
            )
            if ud.get("password"):
                user.set_password(ud["password"])
            db.session.add(user)
            db.session.flush()
            user.set_free_diagram(pickle.dumps({}))
            db.session.flush()
            result["users"].append({"id": user.id, "username": user.username})

        for dd in data.get("diagrams", []):
            diagram = Diagram(
                user_id=dd["user_id"],
                data=pickle.dumps(dd.get("data", {})),
            )
            db.session.add(diagram)
            db.session.flush()
            result["diagrams"].append({"id": diagram.id, "user_id": diagram.user_id})

        # Auto-create licenses + activation for each user so the app
        # doesn't show license modals. Beta builds only honor LICENSE_BETA.
        for user_info in result["users"]:
            uid = user_info["id"]
            hw_uuid = data.get("hardware_uuid", "test-hardware-uuid")
            machine = Machine(user_id=uid, name="Test Machine", code=hw_uuid)
            db.session.add(machine)
            db.session.flush()
            for code, product in [
                (
                    btcopilot.LICENSE_PROFESSIONAL_MONTHLY,
                    btcopilot.LICENSE_PROFESSIONAL,
                ),
                (btcopilot.LICENSE_BETA, btcopilot.LICENSE_BETA),
            ]:
                policy = Policy(
                    code=code,
                    product=product,
                    name=f"Test {product}",
                    interval="month",
                    amount=0,
                    maxActivations=10,
                    active=True,
                    public=True,
                )
                db.session.add(policy)
                db.session.flush()
                lic = License(user_id=uid, policy=policy)
                db.session.add(lic)
                db.session.flush()
                activation = Activation(license_id=lic.id, machine_id=machine.id)
                db.session.add(activation)
                db.session.flush()

        db.session.commit()
        return jsonify(result)

    @app.route("/test/diagrams/<int:diagram_id>", methods=["GET"])
    def test_read_diagram(diagram_id):
        """Return raw pickle bytes. Use pickle.loads() on the response content."""
        diagram = Diagram.query.get(diagram_id)
        if not diagram:
            return jsonify({"success": False, "error": "Not found"}), 404
        from flask import Response

        return Response(diagram.data or b"", mimetype="application/octet-stream")

    @app.route("/test/diagrams/<int:diagram_id>", methods=["PUT"])
    def test_update_diagram(diagram_id):
        """Accept raw pickle bytes as request body."""
        diagram = Diagram.query.get(diagram_id)
        if not diagram:
            return jsonify({"success": False, "error": "Not found"}), 404
        diagram.data = request.data
        db.session.commit()
        return jsonify({"success": True})

    @app.route("/test/diagrams/seed_pickle", methods=["POST"])
    def test_seed_pickle():
        """Seed a diagram from raw pickle bytes (preserves Qt types).
        Send pickle bytes as request body with Content-Type: application/octet-stream.
        Query params: user_id (required), name (optional).
        """
        user_id = request.args.get("user_id", type=int)
        name = request.args.get("name", "")
        if not user_id:
            return jsonify({"success": False, "error": "user_id required"}), 400
        diagram = Diagram(user_id=user_id, data=request.data, name=name)
        db.session.add(diagram)
        db.session.flush()
        db.session.commit()
        return jsonify({"success": True, "id": diagram.id})

    @app.route("/test/reset", methods=["POST"])
    def test_reset():
        db.drop_all()
        db.create_all()
        return jsonify({"success": True})

    @app.route("/test/health", methods=["GET"])
    def test_health():
        return jsonify({"success": True, "status": "ready"})


def main():
    parser = argparse.ArgumentParser(description="Ephemeral btcopilot server")
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--db-dir", type=str, required=True)
    args = parser.parse_args()

    _disable_heavy_extensions()
    _mock_passwords()

    from btcopilot.app import create_app
    from btcopilot.extensions import db

    db_path = os.path.join(args.db_dir, "test.db")

    config = {
        "TESTING": True,
        "CONFIG": "development",
        "SECRET_KEY": "ephemeral-test-key",
        "SQLALCHEMY_DATABASE_URI": f"sqlite:///{db_path}",
        "SQLALCHEMY_TRACK_MODIFICATIONS": False,
        "STRIPE_ENABLED": False,
        "SCHEDULER_API_ENABLED": False,
        "FD_DIR": args.db_dir,
        "WTF_CSRF_CHECK_DEFAULT": False,
        "CELERY_BROKER_URL": "memory://",
        "CELERY_RESULT_BACKEND": "cache+memory://",
    }

    app = create_app(config=config)
    _register_test_routes(app)

    with app.app_context():
        db.create_all()

    # Signal readiness to parent process
    print(f"READY:{args.port}", flush=True)

    def handle_sigterm(sig, frame):
        logger.info("Received SIGTERM, shutting down")
        sys.exit(0)

    signal.signal(signal.SIGTERM, handle_sigterm)

    app.run(host="127.0.0.1", port=args.port, debug=False, use_reloader=False)


if __name__ == "__main__":
    main()
