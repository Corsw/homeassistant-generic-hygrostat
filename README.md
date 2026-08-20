# Generic Hygrostat for Home Assistant

A custom Home Assistant integration that detects **rapid rises in relative humidity** and exposes the result as a binary sensor.

It is especially useful for bathroom ventilation, where a fixed humidity threshold is often unreliable because normal indoor humidity varies with the weather and the seasons.

Instead of asking:

> Is the humidity above a fixed value?

Generic Hygrostat asks:

> Has the humidity risen significantly compared with the recent baseline?

This makes it possible to detect events such as showering without having to continuously adjust a fixed humidity threshold.

> [!IMPORTANT]
> This custom integration is **not the same as the Generic Hygrostat included with Home Assistant Core**.
> See [Difference from Home Assistant's built-in Generic Hygrostat](#difference-from-home-assistants-built-in-generic-hygrostat) below.

---

## Project status

This project was originally created and maintained by **Bas Schipper (`@basschipper`)**.

Many thanks to Bas for creating the integration, maintaining it over the years, and making it possible for the project to continue under new maintainership.

Starting with **v0.9.0**, maintenance has been taken over by **`@Corsw`** and active development has resumed.

Version 0.9.0 is intentionally focused on:

* modernizing the integration for current Home Assistant versions;
* improving reliability and startup behaviour;
* improving availability handling;
* improving diagnostics;
* preserving compatibility with existing installations.

Suggestions, bug reports and pull requests are very welcome. If you have an idea for improving the detection logic, configuration, diagnostics or Home Assistant integration, please open an issue and describe your use case.

### Roadmap

For the release following v0.9.0, the intention is to further modernize the integration with features such as:

* configuration through the Home Assistant UI;
* editable options through the UI;
* a migration path for existing YAML users;
* improved diagnostics;
* automated testing and validation.

Longer term, the legacy naming/domain overlap with Home Assistant Core will also be evaluated carefully. Backwards compatibility for existing users is a priority, so such changes will not be made casually.

---

## Difference from Home Assistant's built-in Generic Hygrostat

Home Assistant includes its own integration called **Generic Hygrostat**. Despite sharing the historical name, the two integrations solve different problems.

|                                | This custom integration       | Home Assistant built-in Generic Hygrostat |
| ------------------------------ | ----------------------------- | ----------------------------------------- |
| Primary purpose                | Detect a rapid humidity rise  | Maintain a target humidity                |
| Typical use case               | Bathroom/shower ventilation   | Humidifier or dehumidifier control        |
| Reference                      | Recent humidity baseline      | Configured target humidity                |
| Output                         | Binary sensor (`on` / `off`)  | Hygrostat entity controlling a switch     |
| Controls a fan/switch directly | No                            | Yes                                       |
| Seasonal humidity changes      | Adapts to the recent baseline | Uses the configured target                |
| Configuration in v0.9.0        | YAML                          | UI helper or YAML                         |

The Home Assistant built-in Generic Hygrostat is the better choice when you want to maintain a room at a specific humidity level.

This custom integration is intended for cases where the **change in humidity** is more important than the absolute humidity value.

A bathroom is a good example:

* 60% relative humidity may be completely normal on one day;
* 60% may be unusually high on another day;
* but a rise from 52% to 58% over a short period is a strong indication that someone may be showering.

The integration detects that rise and turns its binary sensor `on`. You can then use a Home Assistant automation to switch a ventilation fan.

### Legacy domain overlap

This project historically uses the `generic_hygrostat` integration domain, which is also used by the built-in Home Assistant integration.

Because custom integrations take precedence over Core integrations with the same domain, Home Assistant may display a warning that this custom integration overrides a built-in component.

This is a known legacy limitation.

The domain is deliberately **not changed in v0.9.0**, because doing so would require a migration for every existing user. A future release may address this with a carefully designed migration path.

---

## How it works

The integration periodically samples a humidity sensor and keeps a recent history of those samples.

By default:

* the sample interval is **5 minutes**;
* enough samples are stored to cover approximately **15 minutes**;
* a humidity rise of **3 percentage points** triggers the hygrostat.

The basic calculation is:

```text
humidity delta = current humidity - lowest recent humidity
```

If:

```text
humidity delta >= delta_trigger
```

the binary sensor switches to `on`.

### Example

Recent samples:

```text
54.0%
54.5%
55.0%
58.0%
```

The lowest recent value is:

```text
54.0%
```

The current value is:

```text
58.0%
```

So:

```text
58.0 - 54.0 = 4.0
```

With:

```yaml
delta_trigger: 3
```

the hygrostat switches on.

---

## Dehumidification target

When the hygrostat switches on, it calculates a target based on the recent minimum:

```text
target = lowest recent humidity + target_offset
```

The target will never be lower than `min_humidity`.

For example:

```text
Lowest recent humidity: 54%
target_offset:           3%
Calculated target:      57%
```

The hygrostat remains active until the humidity returns to the target, subject to the configured minimum and maximum on-times.

The target is fixed when the hygrostat turns on. It is cleared when the hygrostat turns off.

---

## Timers

### Minimum on-time

`min_on_time` prevents the hygrostat from turning off too quickly after a humidity rise is detected.

This can be useful for bathroom fans that should run for at least a certain amount of time.

Example:

```yaml
min_on_time: 300
```

This keeps the hygrostat active for at least 5 minutes.

### Maximum on-time

`max_on_time` acts as a safety limit.

Example:

```yaml
max_on_time: 7200
```

This limits one active period to approximately 2 hours.

The maximum on-time is also checked when the humidity source sensor is temporarily unavailable.

Because the integration evaluates its timers during periodic updates, the actual switch-off may occur up to approximately one `sample_interval` after the configured maximum time.

---

## Installation

### HACS

1. Open HACS.
2. Go to **Integrations**.
3. Search for **Generic Hygrostat**.
4. Download the integration.
5. Restart Home Assistant.
6. Add the YAML configuration described below.

Existing HACS users do not need to reinstall the integration because of the change in project maintainership.

### Manual installation

1. Download or clone this repository.
2. Copy:

```text
custom_components/generic_hygrostat
```

to:

```text
<your Home Assistant config directory>/custom_components/generic_hygrostat
```

3. Restart Home Assistant.
4. Add the YAML configuration described below.

---

## Configuration

Version 0.9.0 is configured through YAML.

### Minimal example

```yaml
binary_sensor:
  - platform: generic_hygrostat
    name: Bathroom Hygrostat
    sensor: sensor.bathroom_humidity
    unique_id: bathroom_hygrostat
```

A `unique_id` is optional, but strongly recommended. It allows Home Assistant to register the entity in the entity registry so that its name, entity ID and other properties can be managed through the UI.

---

## Full configuration example

```yaml
binary_sensor:
  - platform: generic_hygrostat
    name: Bathroom Hygrostat
    unique_id: bathroom_hygrostat

    # Humidity source
    sensor: sensor.bathroom_humidity

    # Optional: read humidity from an entity attribute instead of its state
    # attribute: humidity

    # Humidity rise required to activate
    delta_trigger: 3

    # Offset from the recent minimum used as the switch-off target
    target_offset: 3

    # Minimum time the hygrostat remains on
    min_on_time: 300

    # Maximum safety on-time
    max_on_time: 7200

    # Time between humidity samples
    sample_interval: 300

    # Do not activate below this absolute humidity level
    min_humidity: 30
```

Time values may be configured using Home Assistant time-period formats. Integer values represent seconds.

---

## Configuration options

| Option            | Required | Default        | Description                                                                |
| ----------------- | -------- | -------------- | -------------------------------------------------------------------------- |
| `name`            | Yes      | —              | Name of the binary sensor.                                                 |
| `sensor`          | Yes      | —              | Entity ID of the humidity source sensor.                                   |
| `attribute`       | No       | —              | Read humidity from this attribute instead of the sensor state.             |
| `delta_trigger`   | No       | `3`            | Humidity increase in percentage points required to activate the hygrostat. |
| `target_offset`   | No       | `3`            | Offset added to the recent minimum to calculate the switch-off target.     |
| `min_on_time`     | No       | `0` seconds    | Minimum time the hygrostat remains active.                                 |
| `max_on_time`     | No       | `7200` seconds | Maximum safety on-time.                                                    |
| `sample_interval` | No       | `300` seconds  | Interval between humidity samples. Must be greater than zero.              |
| `min_humidity`    | No       | `0`            | Absolute humidity level below which the hygrostat will not activate.       |
| `unique_id`       | No       | —              | Stable unique identifier used by the Home Assistant entity registry.       |

---

## Choosing a sample interval

The integration keeps enough samples to represent approximately 15 minutes of recent humidity history.

For example:

```text
sample_interval: 300 seconds
15 minutes / 5 minutes = 3 samples
```

or:

```text
sample_interval: 30 seconds
15 minutes / 30 seconds = 30 samples
```

A shorter interval reacts more quickly and provides more detailed sampling, but also causes more frequent entity updates.

For most installations, start with the default and only shorten the interval if faster shower detection is required.

---

## States and availability

The integration creates a binary sensor.

### `off`

No active humidity rise is being handled.

Default icon:

```text
mdi:water-outline
```

### `on`

A humidity rise has been detected and the hygrostat is active.

Default icon:

```text
mdi:water-plus
```

### `unavailable`

The configured humidity source currently cannot provide a usable value.

This may occur when:

* the source entity does not exist yet during Home Assistant startup;
* the source state is `unknown`;
* the source state is `unavailable`;
* the configured source attribute is unavailable;
* the humidity value cannot be converted to a number.

Default icon:

```text
mdi:water-off
```

Temporary `unknown` and `unavailable` states are treated as normal availability conditions and do not generate unnecessary warnings during Home Assistant startup.

Actual invalid values or configuration problems are still logged as warnings.

---

## Diagnostic attributes

The binary sensor exposes additional attributes to help understand why it changed state.

Example while inactive:

```text
number_of_samples: 30
lowest_sample: 54.8
target: Inactive (hygrostat is off)
min_on_timer: Inactive
max_on_timer: Inactive
min_humidity: 35
```

Example while active:

```text
number_of_samples: 30
lowest_sample: 54.8
target: 57.80 %RH
min_on_timer: Active until 2026-08-20 13:30:00
max_on_timer: Active until 2026-08-20 14:29:00
min_humidity: 35
```

These attributes are primarily intended for diagnostics and debugging.

In particular, the formatted target and timer attributes should be considered display/debug values rather than a stable interface for automations.

---

## Fan automation example

Generic Hygrostat intentionally does **not** control the ventilation fan itself.

This keeps detection logic separate from the action you want Home Assistant to perform.

### Turn the fan on

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
```

### Turn the fan off

It is recommended to also turn the fan off when the hygrostat becomes unavailable.

```yaml
automation:
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

Replace the entity IDs with the entities used in your installation.

---

## What's new in v0.9.0

Version 0.9.0 is primarily a **modernization and reliability release**.

It intentionally preserves the existing humidity-rise detection concept and YAML configuration while updating the implementation for modern Home Assistant versions.

Highlights include:

* migrated the entity to `BinarySensorEntity`;
* modernized the Home Assistant entity lifecycle;
* periodic updates are registered after the entity has been added to Home Assistant;
* interval callbacks are automatically cleaned up when the entity is removed;
* disabled unnecessary Home Assistant polling because the integration manages its own update interval;
* improved handling of missing source sensors during startup;
* `unknown` and `unavailable` source states are treated as temporary availability conditions;
* the hygrostat itself becomes `unavailable` when its source cannot provide a valid humidity value;
* genuine invalid values and missing attributes still produce warnings;
* `sample_interval` is validated and must be greater than zero;
* the sample buffer always contains at least one slot;
* delta calculations safely handle an empty sample history;
* maximum on-time is checked even when the humidity source becomes unavailable;
* prevents immediate reactivation in the same update after `max_on_time` is reached;
* migrated custom attributes to `extra_state_attributes`;
* improved diagnostic output for targets and timers;
* added state-dependent water icons;
* updated project ownership and metadata;
* refreshed documentation for current Home Assistant versions.

### Upgrade notes

Existing YAML configurations are intended to remain compatible with v0.9.0.

No configuration migration should be required.

One behaviour change is worth noting:

> If the humidity source becomes unavailable, the Generic Hygrostat binary sensor now also becomes `unavailable`.

If an automation currently switches a fan off only when the hygrostat changes to `off`, consider also handling the `unavailable` state as shown in the automation example above.

---

## Reporting issues

When reporting a problem, please include as much of the following information as possible:

* Home Assistant version;
* Generic Hygrostat version;
* relevant YAML configuration;
* humidity source entity type;
* relevant Home Assistant log messages;
* what you expected to happen;
* what actually happened.

Please remove passwords, tokens and other sensitive information before posting configuration or logs.

Feature requests and suggestions are welcome as well. Real-world examples are especially useful when discussing humidity-rise detection behaviour.

---

## Contributing

Contributions are welcome.

If you want to propose a change:

1. Open an issue first for larger behavioural changes so the approach can be discussed.
2. Keep backwards compatibility in mind.
3. Explain the use case the change is intended to solve.
4. Test changes against a current Home Assistant installation where possible.
5. Submit a pull request with a clear description of the behaviour before and after the change.

The aim is to keep Generic Hygrostat simple, predictable and useful while gradually bringing the integration in line with modern Home Assistant development practices.

---

## Credits

Generic Hygrostat was originally created by **Bas Schipper (`@basschipper`)**.

The project was inspired by the humidity-control concept used in Domoticz.

Thanks to Bas, previous contributors, issue reporters and users who have helped improve the integration over the years.

Maintenance from v0.9.0 onward is continued by **`@Corsw`**.

Feedback, suggestions and contributions are welcome.
