"""
Adds support for generic hygrostat units.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/binary_sensor.generic_hygrostat/
"""

import collections
from datetime import datetime, timedelta
import logging

import voluptuous as vol

from homeassistant.components.binary_sensor import (
    PLATFORM_SCHEMA,
    BinarySensorEntity,
)
from homeassistant.const import (
    CONF_NAME,
    CONF_UNIQUE_ID,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
)
from homeassistant.core import callback
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.event import async_track_time_interval


_LOGGER = logging.getLogger(__name__)

DEPENDENCIES = ["sensor"]

SAMPLE_DURATION = timedelta(minutes=15)

ATTR_NUMBER_OF_SAMPLES = "number_of_samples"
ATTR_LOWEST_SAMPLE = "lowest_sample"
ATTR_TARGET = "target"
ATTR_MIN_ON_TIMER = "min_on_timer"
ATTR_MAX_ON_TIMER = "max_on_timer"
ATTR_MIN_HUMIDITY = "min_humidity"

CONF_SENSOR = "sensor"
CONF_ATTRIBUTE = "attribute"
CONF_DELTA_TRIGGER = "delta_trigger"
CONF_TARGET_OFFSET = "target_offset"
CONF_MIN_ON_TIME = "min_on_time"
CONF_MAX_ON_TIME = "max_on_time"
CONF_MIN_HUMIDITY = "min_humidity"
CONF_SAMPLE_INTERVAL = "sample_interval"

DEFAULT_DELTA_TRIGGER = 3
DEFAULT_TARGET_OFFSET = 3
DEFAULT_MIN_ON_TIME = timedelta(seconds=0)
DEFAULT_MAX_ON_TIME = timedelta(seconds=7200)
DEFAULT_SAMPLE_INTERVAL = timedelta(minutes=5)
DEFAULT_MIN_HUMIDITY = 0


def positive_sample_interval(value):
    """Validate that the sample interval is greater than zero."""
    interval = cv.time_period(value)

    if interval <= timedelta(0):
        raise vol.Invalid("sample_interval must be greater than zero")

    return interval


PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_NAME): cv.string,
        vol.Required(CONF_SENSOR): cv.entity_id,
        vol.Optional(CONF_ATTRIBUTE): cv.string,
        vol.Optional(
            CONF_DELTA_TRIGGER,
            default=DEFAULT_DELTA_TRIGGER,
        ): vol.Coerce(float),
        vol.Optional(
            CONF_TARGET_OFFSET,
            default=DEFAULT_TARGET_OFFSET,
        ): vol.Coerce(float),
        vol.Optional(
            CONF_MIN_ON_TIME,
            default=DEFAULT_MIN_ON_TIME,
        ): cv.time_period,
        vol.Optional(
            CONF_MAX_ON_TIME,
            default=DEFAULT_MAX_ON_TIME,
        ): cv.time_period,
        vol.Optional(
            CONF_SAMPLE_INTERVAL,
            default=DEFAULT_SAMPLE_INTERVAL,
        ): positive_sample_interval,
        vol.Optional(
            CONF_MIN_HUMIDITY,
            default=DEFAULT_MIN_HUMIDITY,
        ): vol.Coerce(float),
        vol.Optional(CONF_UNIQUE_ID): cv.string,
    }
)


async def async_setup_platform(
    hass,
    config,
    async_add_entities,
    discovery_info=None,
):
    """Set up the Generic Hygrostat platform."""
    async_add_entities(
        [
            GenericHygrostat(
                name=config[CONF_NAME],
                sensor_id=config[CONF_SENSOR],
                sensor_attribute=config.get(CONF_ATTRIBUTE),
                delta_trigger=config[CONF_DELTA_TRIGGER],
                target_offset=config[CONF_TARGET_OFFSET],
                min_on_time=config[CONF_MIN_ON_TIME],
                max_on_time=config[CONF_MAX_ON_TIME],
                sample_interval=config[CONF_SAMPLE_INTERVAL],
                min_humidity=config[CONF_MIN_HUMIDITY],
                unique_id=config.get(CONF_UNIQUE_ID),
            )
        ]
    )


class GenericHygrostat(BinarySensorEntity):
    """Representation of a Generic Hygrostat device."""

    _attr_should_poll = False

    def __init__(
        self,
        *,
        name,
        sensor_id,
        sensor_attribute,
        delta_trigger,
        target_offset,
        min_on_time,
        max_on_time,
        sample_interval,
        min_humidity,
        unique_id,
    ):
        """Initialize the hygrostat."""
        self._attr_name = name
        self._attr_unique_id = unique_id
        self._attr_is_on = False
        self._attr_available = False

        self.sensor_id = sensor_id
        self.sensor_attribute = sensor_attribute
        self.delta_trigger = delta_trigger
        self.target_offset = target_offset
        self.min_on_time = min_on_time
        self.max_on_time = max_on_time
        self.sample_interval = sample_interval
        self.min_humidity = min_humidity

        self.sensor_humidity = None
        self.target = None

        # Store enough samples to cover approximately SAMPLE_DURATION.
        sample_size = max(
            1,
            int(SAMPLE_DURATION / sample_interval),
        )
        self.samples = collections.deque(maxlen=sample_size)

        self.min_on_timer = None
        self.max_on_timer = None

    async def async_added_to_hass(self):
        """Start updates after the entity has been added to Home Assistant."""
        await super().async_added_to_hass()

        # Perform an initial update after the entity is fully registered.
        self._async_update()

        # Register the periodic update and automatically remove it when
        # the entity is removed from Home Assistant.
        self.async_on_remove(
            async_track_time_interval(
                self.hass,
                self._async_update,
                self.sample_interval,
            )
        )

    @callback
    def _async_update(self, now=None):
        """Update the hygrostat state."""
        current_time = datetime.now()
        max_on_time_reached = False

        # Check the maximum on-time even when the humidity sensor is
        # temporarily unavailable.
        if self.max_on_timer and self.max_on_timer <= current_time:
            _LOGGER.debug(
                "Max on timer reached for '%s'",
                self.name,
            )
            self.set_off()
            max_on_time_reached = True

        # Missing, unknown, and unavailable sensors are expected temporary
        # conditions during Home Assistant startup.
        if not self.update_humidity():
            self.async_write_ha_state()
            return

        # Do not immediately switch on again during the same update in which
        # the maximum on-time switched the hygrostat off.
        if max_on_time_reached:
            self.async_write_ha_state()
            return

        if self.min_on_timer and self.min_on_timer > current_time:
            _LOGGER.debug(
                "Minimum time on not yet met for '%s'",
                self.name,
            )
            self.async_write_ha_state()
            return

        if self.target is not None and self.sensor_humidity <= self.target:
            _LOGGER.debug(
                "Dehumidifying target reached for '%s'",
                self.name,
            )
            self.set_off()
            self.async_write_ha_state()
            return

        if self.sensor_humidity < self.min_humidity:
            _LOGGER.debug(
                "Humidity '%s' is below minimum humidity '%s'",
                self.sensor_humidity,
                self.min_humidity,
            )
            self.async_write_ha_state()
            return

        humidity_delta = self.calc_delta()

        if humidity_delta >= self.delta_trigger:
            _LOGGER.debug(
                "Humidity rise detected at '%s' with delta '%s'",
                self.name,
                humidity_delta,
            )
            self.set_on()

        self.async_write_ha_state()

    def update_humidity(self):
        """Update the local humidity value from the source sensor."""
        sensor = self.hass.states.get(self.sensor_id)

        if sensor is None:
            self._attr_available = False
            _LOGGER.debug(
                "Humidity sensor '%s' is not available yet",
                self.sensor_id,
            )
            return False

        if sensor.state in (
            STATE_UNKNOWN,
            STATE_UNAVAILABLE,
        ):
            self._attr_available = False
            _LOGGER.debug(
                "Humidity sensor '%s' has temporary state '%s'",
                self.sensor_id,
                sensor.state,
            )
            return False

        if self.sensor_attribute:
            raw_value = sensor.attributes.get(self.sensor_attribute)
        else:
            raw_value = sensor.state

        if raw_value is None:
            self._attr_available = False
            _LOGGER.warning(
                "Humidity sensor '%s' does not have attribute '%s'",
                self.sensor_id,
                self.sensor_attribute,
            )
            return False

        if raw_value in (
            STATE_UNKNOWN,
            STATE_UNAVAILABLE,
        ):
            self._attr_available = False
            _LOGGER.debug(
                "Humidity sensor '%s' attribute '%s' "
                "has temporary value '%s'",
                self.sensor_id,
                self.sensor_attribute,
                raw_value,
            )
            return False

        try:
            humidity = float(raw_value)
        except (TypeError, ValueError):
            self._attr_available = False
            _LOGGER.warning(
                "Unable to update humidity from sensor '%s' "
                "with value '%s'",
                self.sensor_id,
                raw_value,
            )
            return False

        self._attr_available = True
        self.sensor_humidity = humidity
        self.add_sample(humidity)

        return True

    def add_sample(self, value):
        """Add the given humidity sample to the sample register."""
        self.samples.append(value)

    def calc_delta(self):
        """Calculate the humidity delta."""
        lowest_sample = self.get_lowest_sample()

        if lowest_sample is None or self.sensor_humidity is None:
            return 0

        return self.sensor_humidity - lowest_sample

    def get_lowest_sample(self):
        """Return the lowest humidity sample."""
        try:
            return min(self.samples)
        except ValueError:
            return None

    def set_dehumidification_target(self):
        """Set the dehumidification target."""
        lowest_sample = self.get_lowest_sample()

        if lowest_sample is None or self.target is not None:
            return

        calculated_target = lowest_sample + self.target_offset

        self.target = max(
            self.min_humidity,
            calculated_target,
        )

    def reset_dehumidification_target(self):
        """Unset the dehumidification target."""
        self.target = None

    def set_state(self, state):
        """Set the hygrostat state."""
        self._attr_is_on = state

    def set_min_on_timer(self):
        """Set the minimum on-time timer."""
        if self.min_on_timer is None:
            self.min_on_timer = datetime.now() + self.min_on_time

    def reset_min_on_timer(self):
        """Unset the minimum on-time timer."""
        self.min_on_timer = None

    def set_max_on_timer(self):
        """Set the maximum on-time timer."""
        if self.max_on_timer is None:
            self.max_on_timer = datetime.now() + self.max_on_time

    def reset_max_on_timer(self):
        """Unset the maximum on-time timer."""
        self.max_on_timer = None

    def set_on(self):
        """Set the hygrostat to on."""
        self.set_state(True)
        self.set_dehumidification_target()
        self.set_min_on_timer()
        self.set_max_on_timer()

    def set_off(self):
        """Set the hygrostat to off."""
        self.set_state(False)
        self.reset_dehumidification_target()
        self.reset_min_on_timer()
        self.reset_max_on_timer()

    @property
    def icon(self):
        """Return an icon based on the hygrostat state."""
        if not self._attr_available:
            return "mdi:water-off"

        if self._attr_is_on:
            return "mdi:water-alert"

        return "mdi:water-outline"

    @staticmethod
    def format_timer(timer):
        """Format a timer for debug display."""
        if timer is None:
            return "Inactive"

        return (
            "Active until "
            f"{timer.strftime('%Y-%m-%d %H:%M:%S')}"
        )

    @property
    def extra_state_attributes(self):
        """Return entity-specific state attributes."""
        lowest_sample = self.get_lowest_sample()

        if self.target is None:
            target = "Inactive (hygrostat is off)"
        else:
            target = f"{self.target:.2f} %RH"

        return {
            ATTR_NUMBER_OF_SAMPLES: len(self.samples),
            ATTR_LOWEST_SAMPLE: (
                round(lowest_sample, 2)
                if lowest_sample is not None
                else "No samples yet"
            ),
            ATTR_TARGET: target,
            ATTR_MIN_ON_TIMER: self.format_timer(
                self.min_on_timer
            ),
            ATTR_MAX_ON_TIMER: self.format_timer(
                self.max_on_timer
            ),
            ATTR_MIN_HUMIDITY: self.min_humidity,
        }
