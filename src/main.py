import asyncio
from threading import Event
from typing import ClassVar, Mapping, Optional, Sequence, cast
from typing_extensions import Self
from viam.logging import getLogger
from viam.module.module import Module
from viam.proto.app.robot import ComponentConfig
from viam.proto.common import ResourceName
from viam.resource.base import ResourceBase
from viam.resource.easy_resource import EasyResource
from viam.resource.types import Model, ModelFamily
from viam.utils import struct_to_dict, ValueTypes
from viam.components.sensor import Sensor
from viam.components.board import Board
from viam.services.generic import Generic as GenericServiceBase
from viam.components.generic import Generic as GenericComponent

LOGGER = getLogger("mmwave-rgbled")

class MmwaveRgbled(GenericServiceBase, EasyResource):
    MODEL: ClassVar[Model] = Model(
        ModelFamily("joyce", "presence-detector"), "mmwave-rgbled")

    auto_start = True
    task = None
    event = Event()

    @classmethod
    def new(
        cls, config: ComponentConfig, dependencies: Mapping[ResourceName, ResourceBase]
    ) -> Self:
        """Factory method to create a new instance."""
        return super().new(config, dependencies)

    @classmethod
    def validate_config(cls, config: ComponentConfig) -> Sequence[str]:
        fields = struct_to_dict(config.attributes)
        required_keys = ["board", "sensor", "rgb_led"]

        for key in required_keys:
            if key not in fields or not isinstance(fields[key], str):
                raise ValueError(f"{key} must be a string and included in the configuration.")

        return [str(name) for name in fields.values()]

    def reconfigure(
        self, config: ComponentConfig, dependencies: Mapping[ResourceName, ResourceBase]
    ):
        """Update resource configuration dynamically."""
        attrs = struct_to_dict(config.attributes)
        self.auto_start = bool(attrs.get("auto_start", self.auto_start))

        # Fetch sensor
        sensor_resource = dependencies.get(
            Sensor.get_resource_name(str(attrs.get("sensor")))
        )
        self.sensor = cast(Sensor, sensor_resource)

        # Fetch RGB LED
        rgb_led_resource = dependencies.get(
            GenericComponent.get_resource_name(str(attrs.get("rgb_led")))
        )
        self.rgb_led = cast(GenericComponent, rgb_led_resource)

        # Start the LED loop after the ripple effect finishes
        if self.auto_start:
            self.start()

        return super().reconfigure(config, dependencies)

    async def on_loop(self):
        """Continuously fetch sensor readings and update LED color."""
        color_mappings = {
            "No Target": {"red": 0.0, "green": 0.0, "blue": 1.0},  # Blue
            "Moving Target": {"red": 1.0, "green": 0.0, "blue": 0.0},  # Red
            "Static Target": {"red": 0.0, "green": 1.0, "blue": 0.0},  # Green
            "Moving and Static Targets": {"red": 1.0, "green": 0.0, "blue": 1.0},  # Purple
        }

        # Run the ripple effect once before starting LED updates
        if self.rgb_led:
            LOGGER.info("Triggering ripple effect on startup.")
            await self.rgb_led.do_command({"ripple": {"duration": 2.0}})

        last_color = None
        while not self.event.is_set():
            try:
                readings = await self.sensor.get_readings() if self.sensor else {}
                # LOGGER.info(f"Sensor Readings: {readings}")

                # Parse detection status
                detection_status = readings.get("detection_status", "No Target")
                color = color_mappings.get(detection_status, {"red": 0.0, "green": 0.0, "blue": 1.0})  # Default: Blue
                LOGGER.info(f"Detection Status: {detection_status}")

                # ✅ Resend LED command every 5 seconds to ensure persistence
                if self.rgb_led and (color != last_color or (self.task and self.task.done())):
                    # LOGGER.info(f"Ensuring LED stays on with {color}")
                    await self.rgb_led.do_command({
                        "control_rgb_led": {
                            "red": color["red"],
                            "green": color["green"],
                            "blue": color["blue"],
                        }
                    })
                    last_color = color

            except Exception as e:
                LOGGER.error(f"Error updating LED: {e}")

            await asyncio.sleep(1)  # Keep updating every second

    def start(self):
        """Start background loop only if not already running."""
        if self.task is None or self.task.done():
            self.event.clear()  # Ensures loop runs
            self.task = asyncio.create_task(self.control_loop())

    def stop(self):
        """Stop the service loop gracefully."""
        self.event.set()
        if self.task is not None:
            self.task.cancel()

    async def control_loop(self):
        """Persistent control loop handling LED updates."""
        while not self.event.is_set():
            await self.on_loop()
            await asyncio.sleep(0)

    def __del__(self):
        self.stop()

    async def close(self):
        self.stop()

if __name__ == "__main__":
    asyncio.run(Module.run_from_registry())