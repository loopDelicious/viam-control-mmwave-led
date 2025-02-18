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
from viam.services.generic import Generic
from viam.components.generic import Generic

LOGGER = getLogger("mmwave-rgbled")

class MmwaveRgbled(Generic, EasyResource):
    MODEL: ClassVar[Model] = Model(
        ModelFamily("joyce", "presence-detector"), "mmwave-rgbled"
    )

    auto_start = True
    task = None
    event = Event()

    @classmethod
    def new(
        cls, config: ComponentConfig, dependencies: Mapping[ResourceName, ResourceBase]
    ) -> Self:
        """Factory method to create a new instance."""
        instance = super().new(config, dependencies)

        # Initialize attributes
        instance.stop_event = asyncio.Event()
        instance.task_readings = None
        instance.task_led_status = None

        return instance

    @classmethod
    def validate_config(cls, config: ComponentConfig) -> Sequence[str]:
        fields = struct_to_dict(config.attributes)
        required_keys = ["board", "sensor", "rgb_led"]

        for key in required_keys:
            if key not in fields or not isinstance(fields[key], str):
                raise ValueError(f"{key} must be a string and included in the configuration.")

        return []

    def reconfigure(
        self, config: ComponentConfig, dependencies: Mapping[ResourceName, ResourceBase]
    ):
        """Update resource configuration dynamically."""
        attrs = struct_to_dict(config.attributes)
        
        # Fetch board
        board_resource = dependencies.get(
            Board.get_resource_name(str(attrs.get("board")))
        )
        self.board = cast(Board, board_resource)

        # Fetch sensor
        sensor_resource = dependencies.get(
            Sensor.get_resource_name(str(attrs.get("sensor")))
        )
        self.sensor = cast(Sensor, sensor_resource)

        # Fetch RGB LED
        rgb_led_resource = dependencies.get(
            Generic.get_resource_name(str(attrs.get("rgb_led")))
        )
        self.rgb_led = cast(Generic, rgb_led_resource)

        # Stop any existing tasks before starting new ones
        self.stop_tasks()

        # Start background tasks
        self.task_readings = asyncio.create_task(self.get_readings())
        self.task_led_status = asyncio.create_task(self.update_led_status())

        return super().reconfigure(config, dependencies)

    async def get_readings(self):
        """Continuously fetch and log sensor readings."""
        while not self.stop_event.is_set():
            readings = await self.sensor.get_readings() if self.sensor else "unknown"
            self.logger.info(f"Sensor Readings: {readings}")
            LOGGER.info("Getting sensor readings.")

            # Trigger a ripple effect
            if self.rgb_led:
                await self.rgb_led.do_command({"ripple": {"duration": 2.0}})

            await asyncio.sleep(1)

    async def update_led_status(self):
        """Continuously update the RGB LED status based on sensor readings."""
        color_mappings = {
            "0": {"red": 0.0, "green": 0.0, "blue": 1.0},  # No target - Blue
            "1": {"red": 1.0, "green": 0.0, "blue": 0.0},  # Moving target - Red
            "2": {"red": 0.0, "green": 1.0, "blue": 0.0},  # Static target - Green
            "3": {"red": 1.0, "green": 1.0, "blue": 0.0},  # Moving and static targets - Yellow
        }

        while not self.stop_event.is_set():
            readings = await self.sensor.get_readings() if self.sensor else "unknown"
            color = color_mappings.get(str(readings), {"red": 1.0, "green": 1.0, "blue": 1.0})  # Default: White

            if self.rgb_led:
                await self.rgb_led.control_rgb_led(**color)

            await asyncio.sleep(1)

    async def do_command(
        self,
        command: Mapping[str, ValueTypes],
        *,
        timeout: Optional[float] = None,
        **kwargs
    ) -> Mapping[str, ValueTypes]:
        """Handle commands sent to the service."""
        result = {key: False for key in command.keys()}
        for name, _args in command.items():
            if name == "start":
                self.start_tasks()
                result[name] = True
            elif name == "stop":
                self.stop_tasks()
                result[name] = True
        return result

    def start_tasks(self):
        """Start background tasks if not already running."""
        if not self.task_readings or self.task_readings.done():
            self.task_readings = asyncio.create_task(self.get_readings())
        if not self.task_led_status or self.task_led_status.done():
            self.task_led_status = asyncio.create_task(self.update_led_status())

    def stop_tasks(self):
        """Stop background tasks gracefully."""
        self.stop_event.set()
        for task in [self.task_readings, self.task_led_status]:
            if task and not task.done():
                task.cancel()

    async def close(self):
        """Cleanup tasks on shutdown."""
        self.stop_tasks()

if __name__ == "__main__":
    asyncio.run(Module.run_from_registry())
