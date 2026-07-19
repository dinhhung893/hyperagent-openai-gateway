"""Run the CLI without a console script:  python -m gateway [args]

This is identical to the `hyperagent-gateway` / `hga` command, but avoids PATH/
shim problems on machines with multiple Python installs. Examples:
    python -m gateway serve --upstream mock
    python -m gateway agents --upstream mock
    python -m gateway login
"""
from .cli import main

if __name__ == "__main__":
    raise SystemExit(main())
