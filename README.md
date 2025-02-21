# Module control-mmwave-led

The [`presence-detector`](https://app.viam.com/module/joyce/presence-detector) module uses an LD2410C mmwave sensor to detect presence and display a visual indicator with an RGB LED.

## Model joyce:control-mmwave-led:mmwave-rgbled

The state detected by the mmwave sensor displays the following colors on an RGB LED:

| Detection Status            | Color  |
| --------------------------- | ------ |
| `No Target`                 | Blue   |
| `Moving Target`             | Red    |
| `Static Target`             | Green  |
| `Moving and Static Targets` | Purple |

These colors can be customized with an optional `color_attributes` in the configuration. See details below.

If you wish to further customize your own logic, you can [create your own module](https://docs.viam.com/operate/get-started/other-hardware/hello-world-module/) using this repository as a starting point.

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
| `color_attributes` | object | Optional  | RGB values for each detected state       |

#### Example Configuration

```json
{
  "board": "board-1",
  "rgb_led": "rgb-led",
  "sensor": "mmwave-sensor",
  "color_attributes": {
    "no_target": {
      "red": 0.1,
      "green": 0.1,
      "blue": 0.8
    },
    "moving_target": {
      "red": 1,
      "green": 0.5,
      "blue": 0
    },
    "static_target": {
      "red": 0,
      "green": 1,
      "blue": 0.5
    },
    "moving_and_static_targets": {
      "red": 1,
      "green": 0.2,
      "blue": 1
    }
  }
}
```
