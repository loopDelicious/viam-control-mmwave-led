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
        ModelFamily("joyce", "presence-detector"), "mmwave-rgbled"
    )

    auto_start = True
    task = None
    event = Event()

    DEFAULT_COLORS = {
        "No Target": {"red": 0.0, "green": 0.0, "blue": 1.0},  # Blue
        "Moving Target": {"red": 1.0, "green": 0.0, "blue": 0.0},  # Red
        "Static Target": {"red": 0.0, "green": 1.0, "blue": 0.0},  # Green
        "Moving and Static Targets": {"red": 1.0, "green": 0.0, "blue": 1.0},  # Purple
    }

    @classmethod
    def new(
        cls, config: ComponentConfig, dependencies: Mapping[ResourceName, ResourceBase]
    ) -> Self:
        return super().new(config, dependencies)

    @classmethod
    def validate_config(cls, config: ComponentConfig) -> Sequence[str]:
        """Validate config and return only required dependencies."""
        fields = struct_to_dict(config.attributes)
        required_keys = ["board", "sensor", "rgb_led"]
        dependencies = []

        for key in required_keys:
            if key in fields and isinstance(fields[key], str):
                dependencies.append(fields[key])
            else:
                raise ValueError(f"{key} must be a string and included in the configuration.")

        return dependencies  

    
    def reconfigure(self, config: ComponentConfig, dependencies: Mapping[ResourceName, ResourceBase]):
        """Update resource configuration dynamically without treating color_attributes as a dependency."""
        attrs = struct_to_dict(config.attributes)
        
        self.auto_start = bool(attrs.get("auto_start", self.auto_start))

        # Fetch required dependencies
        self.sensor = cast(Sensor, dependencies.get(Sensor.get_resource_name(attrs["sensor"])))
        self.rgb_led = cast(GenericComponent, dependencies.get(GenericComponent.get_resource_name(attrs["rgb_led"])))

        # Extract color attributes separately, without affecting attributes dict
        color_config = attrs.pop("color_attributes", {}) 
        self.color_attributes = self.load_color_config(color_config)

        if self.auto_start:
            self.start()

        return super().reconfigure(config, dependencies)

    
    def load_color_config(self, color_attrs: dict) -> dict:
        """Loads user-defined colors if available, otherwise defaults to preset values."""
        color_keys = {
            "no_target": "No Target",
            "moving_target": "Moving Target",
            "static_target": "Static Target",
            "moving_and_static_targets": "Moving and Static Targets"
        }
        custom_colors = {}

        for key, readable_key in color_keys.items():
            custom_color = color_attrs.get(key, {})  
            default_color = self.DEFAULT_COLORS[readable_key]

            if isinstance(custom_color, dict):
                try:
                    validated_color = {
                        "red": min(max(float(custom_color.get("red", default_color["red"])), 0.0), 1.0),
                        "green": min(max(float(custom_color.get("green", default_color["green"])), 0.0), 1.0),
                        "blue": min(max(float(custom_color.get("blue", default_color["blue"])), 0.0), 1.0),
                    }
                    custom_colors[readable_key] = validated_color
                except (ValueError, TypeError):
                    LOGGER.warning(f"Invalid color values for {key}, using default.")
                    custom_colors[readable_key] = default_color
            else:
                custom_colors[readable_key] = default_color

        return custom_colors

    async def on_loop(self):
        """Continuously fetch sensor readings and update LED color without turning off."""

        last_color = None
        last_detection = "No Target"

        # Run ripple effect before normal LED updates
        if self.rgb_led:
            LOGGER.info("Triggering ripple effect on startup.")
            await self.rgb_led.do_command({"ripple": {"duration": 2.0}})
            await asyncio.sleep(2)  

        await self.rgb_led.do_command({"control_rgb_led": {"red": 1.0, "green": 0.0, "blue": 0.0}})

        while not self.event.is_set():
            try:
                readings = await self.sensor.get_readings() if self.sensor else {}
                detection_status = readings.get("detection_status", "No Target")

                # Ensure detection status exists
                if detection_status not in self.color_attributes:
                    LOGGER.warning(f"Unexpected detection status: {detection_status}. Using default color.")
                    detection_status = "No Target"

                color = self.color_attributes[detection_status]
                LOGGER.info(f"Detection Status: {detection_status}, LED Color: {color}")

                # Update LED only if the color actually changes
                if self.rgb_led and color != last_color:
                    LOGGER.info(f"Sending command to LED: {color}")
                    await self.rgb_led.do_command({
                        "control_rgb_led": {
                            "red": color["red"],
                            "green": color["green"],
                            "blue": color["blue"],
                        }
                    })
                    last_color = color  
                else:
                    LOGGER.info("Skipping LED update (color unchanged)")

            except Exception as e:
                LOGGER.error(f"Error updating LED: {e}")

            await asyncio.sleep(1) 

    def start(self):
        """Ensure the control loop is running."""
        if self.task is None or self.task.done():
            self.event.clear()  # Ensures loop runs

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
