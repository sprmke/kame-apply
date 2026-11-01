"""Print the OpenAPI schema as stable JSON (input to packages/api-client generation)."""

import json
import os
import sys

# Importing app.main builds the module-level app, and an unset ENVIRONMENT now means prod.
os.environ.setdefault("ENVIRONMENT", "local")

from app.core.config import Settings
from app.main import create_app


def main() -> None:
    # A non-prod settings object so docs/openapi are enabled; no DB connection is made.
    app = create_app(Settings(environment="local", log_json=False, log_level="ERROR"))
    json.dump(app.openapi(), sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
