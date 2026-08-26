"""Launch one sandbox backend and hold it open until killed.

    uv run --directory <workspace> python familydiagram/mcpserver/ephemeral_server.py \
        --ticket FD-336 --db sqlite --seed family --broker redis --llm stub

Prints `READY:<port>` and `MANIFEST:<json>` on stdout once the server answers its
health check and any seed has been applied; anything short of that is an error
exit, never a silent success. The port is chosen here — callers read it, they
never assume it. See familydiagram/doc/SANDBOX.md.
"""

import argparse
import atexit
import json
import logging
import signal
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mcpserver.sandbox import (
    Broker,
    Db,
    Llm,
    MANIFEST_PREFIX,
    NO_SEED,
    Prompts,
    READY_PREFIX,
    Sandbox,
)


def parse_args(argv=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Sandbox btcopilot backend")
    parser.add_argument("--ticket", help="FD-NNN; selects each repo's worktree")
    parser.add_argument("--port", type=int, help="default: a free port")
    parser.add_argument(
        "--db",
        default=Db.Sqlite.value,
        help=f"{Db.Sqlite.value} | {Db.Sqlite.value}:<dir> | {Db.Prod.value} | <database uri>",
    )
    parser.add_argument(
        "--seed", default=NO_SEED, help=f"profile name | <json file> | {NO_SEED}"
    )
    parser.add_argument(
        "--broker", default=Broker.Memory.value, choices=[b.value for b in Broker]
    )
    parser.add_argument("--llm", default=Llm.Stub.value, choices=[l.value for l in Llm])
    parser.add_argument(
        "--prompts",
        default=Prompts.Auto.value,
        help=f"{Prompts.Auto.value} | {Prompts.Off.value} | <path to private_prompts.py>",
    )
    parser.add_argument("--auto-auth-user", help="email logged in without a password")
    parser.add_argument(
        "--hardware-uuid",
        help="this machine's uuid, so seeded licenses actually activate the apps "
        "(pkdiagram.util.HARDWARE_UUID); omit only for a backend nothing will connect to",
    )
    return parser.parse_args(argv)


def main(argv=None) -> None:
    args = parse_args(argv)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    sandbox = Sandbox(
        ticket=args.ticket,
        port=args.port,
        db=args.db,
        seed=args.seed,
        broker=args.broker,
        llm=args.llm,
        prompts=args.prompts,
        auto_auth_user=args.auto_auth_user,
        hardware_uuid=args.hardware_uuid,
    )
    atexit.register(sandbox.shutdown)
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))
    signal.signal(signal.SIGINT, lambda *_: sys.exit(0))

    print(sandbox.checkouts.describe(), file=sys.stderr, flush=True)
    manifest = sandbox.start()
    print(f"{READY_PREFIX}{sandbox.port}", flush=True)
    print(f"{MANIFEST_PREFIX}{json.dumps(manifest)}", flush=True)
    sandbox.wait()


if __name__ == "__main__":
    main()
