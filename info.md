# Generic Hygrostat for Home Assistant

Generic Hygrostat detects **rapid rises in relative humidity** and exposes the result as a binary sensor.

It is especially useful for bathroom ventilation, where a fixed humidity threshold is often unreliable because normal indoor humidity changes with the weather and the seasons.

Instead of checking whether humidity is above a fixed value, this integration compares the current humidity with the recent baseline.

When a significant rise is detected, the binary sensor switches on. You can then use a Home Assistant automation to control a ventilation fan.

> **Important:** This custom integration is not the same as the Generic Hygrostat included with Home Assistant Core.

## Custom vs built-in Generic Hygrostat

The two integrations solve different problems.

|                                | This custom integration      | Home Assistant built-in         |
| ------------------------------ | ---------------------------- | ------------------------------- |
| Purpose                        | Detect a rapid humidity rise | Maintain a target humidity      |
| Typical use                    | Bathroom/shower detection    | Humidifier/dehumidifier control |
| Reference                      | Recent humidity baseline     | Fixed target humidity           |
| Output                         | Binary sensor                | Hygrostat controlling a switch  |
| Fan/switch controlled directly | No                           | Yes                             |

Use the built-in Home Assistant Generic Hygrostat if you want to maintain a fixed target humidity.

Use this custom integration when the **change in humidity** is more important than the absolute humidity value.

## Project status

This integration was originally created and maintained by **Bas Schipper (`@basschipper`)**.

Many thanks to Bas for creating the project, maintaining it over the years, and allowing its development to continue under new maintainership.

Starting with **v0.9.0**, the project is actively maintained by **`@Corsw`**.

Version 0.9.0 focuses on modernization, reliability, improved Home Assistant compatibility and better diagnostics while preserving compatibility with existing YAML configurations.

Suggestions, bug reports and pull requests are welcome.

A future release is planned to add configuration through the Home Assistant UI and further modernize the integration.

## Installation

### HACS

1. Open HACS.
2. Go to **Integrations**.
3. Search for **Generic Hygrostat**.
4. Download the integration.
5. Restart Home Assistant.
6. Add the YAML configuration below.

### Manual

Copy:

```text
custom_components/generic_hygrostat
```

to:

```text
<your Home Assistant config directory>/custom_components/generic_hygrostat
```

Restart Home Assistant afterwards.

## Configuration

Add the integration under `binary_sensor` in your Home Assistant configuration.

Example:

```yaml
binary_sensor:
  - platform: generic_hygrostat
    name: Bathroom Hygrostat
    unique_id: bathroom_hygrostat
    sensor: sensor.bathroom_humidity
    delta_trigger: 3
    target_offset: 3
    min_on_time: 300
    max_on_time: 7200
    sample_interval: 300
    min_humidity: 30
```

### Available options

| Option            | Default  | Description                                                    |
| ----------------- | -------- | -------------------------------------------------------------- |
| `name`            | required | Name of the binary sensor.                                     |
| `sensor`          | required | Entity ID of the humidity source sensor.                       |
| `attribute`       | none     | Optional attribute containing the humidity value.              |
| `delta_trigger`   | `3`      | Humidity increase in percentage points required to activate.   |
| `target_offset`   | `3`      | Offset above the recent minimum used as the switch-off target. |
| `min_on_time`     | `0`      | Minimum time the hygrostat remains active.                     |
| `max_on_time`     | `7200`   | Maximum safety on-time.                                        |
| `sample_interval` | `300`    | Time between humidity samples.                                 |
| `min_humidity`    | `0`      | Humidity level below which activation is prevented.            |
| `unique_id`       | none     | Stable ID for the Home Assistant entity registry.              |

Integer time values are interpreted as seconds.

## How detection works

The integration periodically samples the humidity sensor and stores approximately 15 minutes of recent measurements.

It calculates:

```text
humidity delta = current humidity - lowest recent humidity
```

When the delta reaches or exceeds `delta_trigger`, the binary sensor switches on.

When activated, a dehumidification target is calculated from the recent minimum plus `target_offset`.

The hygrostat switches off when the humidity returns to that target, while respecting the configured minimum and maximum on-times.

## States

### Off

No active humidity rise is being handled.

Icon:

```text
mdi:water-outline
```

### On

A humidity rise has been detected.

Icon:

```text
mdi:water-plus
```

### Unavailable

The humidity source cannot currently provide a usable value.

Icon:

```text
mdi:water-off
```

Temporary `unknown` and `unavailable` source states are handled gracefully during Home Assistant startup.

Actual invalid sensor values or configuration problems are still logged as warnings.

## Diagnostic attributes

The entity exposes additional attributes to help explain its behaviour:

* number of stored samples;
* lowest recent humidity sample;
* calculated dehumidification target;
* minimum on-time timer;
* maximum on-time timer;
* configured minimum humidity.

Inactive targets and timers are displayed using readable diagnostic text instead of `unknown`.

## Automation example

Generic Hygrostat intentionally does not control a ventilation fan directly.

Example:

```yaml
automation:
  - alias: Bathroom Hygrostat - Fan On
    triggers:
      - trigger: state
        entity_id: binary_sensor.bathroom_hygrostat
        to: "on"

    actions:
      - action: switch.turn_on
        target:
          entity_id: switch.bathroom_fan

  - alias: Bathroom Hygrostat - Fan Off
    triggers:
      - trigger: state
        entity_id: binary_sensor.bathroom_hygrostat
        to: "off"

      - trigger: state
        entity_id: binary_sensor.bathroom_hygrostat
        to: "unavailable"

    actions:
      - action: switch.turn_off
        target:
          entity_id: switch.bathroom_fan
```

Replace the entity IDs with those used in your Home Assistant installation.

## What's new in v0.9.0

Version 0.9.0 modernizes the existing integration while intentionally preserving its humidity-rise detection concept and YAML configuration.

Highlights include:

* modern `BinarySensorEntity` implementation;
* improved Home Assistant entity lifecycle handling;
* automatic cleanup of periodic callbacks;
* improved startup behaviour;
* correct handling of `unknown` and `unavailable` humidity sources;
* entity availability follows source availability;
* improved validation and sample handling;
* safer maximum on-time handling;
* improved diagnostic attributes;
* state-dependent icons;
* updated project ownership and documentation.

Existing YAML configurations are intended to continue working without migration.

## Known legacy limitation

This custom integration historically uses the domain:

```text
generic_hygrostat
```

Home Assistant Core now also contains an integration with that domain.

Home Assistant may therefore display a warning that this custom integration overrides a built-in component.

The domain is deliberately not changed in v0.9.0 because doing so would break existing installations.

A future release may provide a carefully designed migration path.

## Support and contributions

Issues, feature requests and pull requests are welcome.

Please report problems through the [GitHub issue tracker](https://github.com/Corsw/homeassistant-generic-hygrostat/issues).

The full documentation is available in the [project repository](https://github.com/Corsw/homeassistant-generic-hygrostat).
