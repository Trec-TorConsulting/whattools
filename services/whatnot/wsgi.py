"""WSGI entry point for the Whatnot integration service."""

from services.whatnot.app import create_app

app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5006, debug=True)
