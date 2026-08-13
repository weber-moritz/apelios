"""
Watch changed DMX output values published by the fixture layer.

Replaces:  nats sub "output.>"

Usage:
    python tools/scripts/watch_outputs.py
    python tools/scripts/watch_outputs.py 'output.>'
"""
import argparse
import asyncio
import json

import nats


async def main() -> None:
    parser = argparse.ArgumentParser(description="Watch changed Apelios DMX output values")
    parser.add_argument(
        "subject",
        nargs="?",
        default="output.2.>",
        help="NATS subject to watch (default: output.2.>)",
    )
    args = parser.parse_args()

    nc = await nats.connect("nats://127.0.0.1:4222")
    print(f"Watching changed values on {args.subject}  (Ctrl+C to stop)\n")
    previous_values: dict[str, int] = {}

    async def handler(msg) -> None:
        decoded = msg.data.decode()
        try:
            value = int(json.loads(decoded)["value"])
        except (KeyError, TypeError, ValueError, json.JSONDecodeError):
            print(f"[{msg.subject}]  {decoded}")
            return

        if previous_values.get(msg.subject) == value:
            return

        previous_values[msg.subject] = value
        print(f"[{msg.subject}]  {decoded}")

    await nc.subscribe(args.subject, cb=handler)

    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        await nc.drain()


if __name__ == "__main__":
    asyncio.run(main())
