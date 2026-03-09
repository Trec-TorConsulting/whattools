"""WSGI entry point for the inventory service."""

from services.inventory.app import create_app

app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5002, debug=True)
