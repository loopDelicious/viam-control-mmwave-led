# Module control-mmwave-led

Use an mmwave sensor to detect presence and display a visual indicator with an RGB LED.

## Model joyce:control-mmwave-led:mmwave-rgbled

The state detected by the mmwave sensor displays the following colors on an RGB LED:

| Detection Status            | Color  |
| --------------------------- | ------ |
| `No Target`                 | Blue   |
| `Moving Target`             | Red    |
| `Static Target`             | Green  |
| `Moving and Static Targets` | Purple |

If you wish to customize your own logic, you can [create your own module](https://docs.viam.com/operate/get-started/other-hardware/hello-world-module/) using this repository as a starting point.

### Configuration

The following attribute template can be used to configure this model:

```json
{
  "board": <string>,
  "sensor": <string>,
  "rgb_led": <string>
}
```

#### Attributes

The following attributes are available for this model:

| Name      | Type   | Inclusion | Description                                             |
| --------- | ------ | --------- | ------------------------------------------------------- |
| `board`   | string | Required  | The name of the Raspberry Pi board in the Viam app      |
| `sensor`  | string | Required  | The name of the mmwave sensor component in the Viam app |
| `rgb_led` | string | Required  | The name of the RGB LED component in the viam app       |

#### Example Configuration

```json
{
  "board": "board-1",
  "sensor": "mmwave-sensor",
  "rgb_led": "generic-1"
}
```
