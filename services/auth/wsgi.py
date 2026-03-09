"""WSGI entry point for the auth service."""

from services.auth.app import create_app

app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)
