"""
Watch mapped output state published by the middleware layer.

Replaces:  nats sub "output.>"

Usage:
    python scripts/watch_outputs.py
"""
import asyncio
import nats


async def main() -> None:
    nc = await nats.connect("nats://127.0.0.1:4222")
    print("Watching output.>  (Ctrl+C to stop)\n")

    async def handler(msg) -> None:
        print(f"[{msg.subject}]  {msg.data.decode()}")

    await nc.subscribe("output.>", cb=handler)

    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        await nc.drain()


if __name__ == "__main__":
    asyncio.run(main())
