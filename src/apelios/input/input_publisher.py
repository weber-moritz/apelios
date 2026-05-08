"""Input-side publisher facade used by input adapters."""

import json


class InputPublisher:
    def __init__(self, input_publish_prefix: str, broker_client: object) -> None:
        self.broker_client = broker_client
        self.input_publish_prefix = input_publish_prefix

    async def publish(self, device: str = "", axis: str = "", value: float = 0.0) -> None:
        """Publish one normalized adapter event through the broker."""
        if device is None or axis is None or value is None:
            raise ValueError("device, axis or value are empty")

        if (
            not device
            or not axis
            or isinstance(device, (bytes, float, int))
            or isinstance(axis, (bytes, float, int))
            or isinstance(value, str)
        ):
            raise TypeError("device, axis or value have the wrong type")

        subject = self.input_publish_prefix + "." + device
        msg = json.dumps({"source": f"{device}.{axis}", "value": value}).encode("utf-8")

        await self.broker_client.publish(subject, msg)