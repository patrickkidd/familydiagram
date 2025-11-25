"""
Map Server runner script.

This script is used to start the Map Server as a subprocess.
Usage:
    python -m pkdiagram.mapserver.runner --port 8765 --headless
"""

import argparse
import logging
import sys


def main():
    parser = argparse.ArgumentParser(description="Run the Map Server for UI testing")
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Host to bind to (default: 127.0.0.1)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8765,
        help="Port to listen on (default: 8765)",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run in headless mode (no display)",
    )
    parser.add_argument(
        "--snapshot-dir",
        help="Directory for storing snapshots",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging level (default: INFO)",
    )
    parser.add_argument(
        "--log-file",
        help="Log file path (default: stderr)",
    )

    args = parser.parse_args()

    # Configure logging
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    log_handlers = []

    if args.log_file:
        log_handlers.append(logging.FileHandler(args.log_file))
    else:
        log_handlers.append(logging.StreamHandler(sys.stderr))

    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format=log_format,
        handlers=log_handlers,
    )

    log = logging.getLogger(__name__)
    log.info(f"Starting Map Server on {args.host}:{args.port}")

    # Import and run server
    from pkdiagram.mapserver import MapServer

    server = MapServer(
        port=args.port,
        host=args.host,
        headless=args.headless,
    )

    # Set snapshot directory if provided
    if args.snapshot_dir:
        server._snapshotManager.snapshotDir = args.snapshot_dir

    try:
        server.run()
    except KeyboardInterrupt:
        log.info("Shutting down...")
        server.stop()
    except Exception as e:
        log.exception(f"Server error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
