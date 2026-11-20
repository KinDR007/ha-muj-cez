"""Constants for the Muj CEZ integration."""

from datetime import timedelta

DOMAIN = "muj_cez"
MANUFACTURER = "ČEZ"
PORTAL_URL = "https://muj.cez.cz"

CONF_UPDATE_PERIOD = "update_period"
CONF_UPDATE_TIME = "update_time"
CONF_REFERENCE_SENSOR = "reference_sensor"
CONF_REFERENCE_EXPORT_SENSOR = "reference_export_sensor"
CONF_SPOT_PRICE_SENSOR = "spot_price_sensor"
CONF_DASHBOARD = "dashboard"
CONF_INSTALL_CARDS = "install_cards"
# HDO switching times from the ČEZ Distribuce portal (same credentials).
CONF_PARTNER = "partner"
CONF_HDO = "hdo"

# Dashboard option values: "none" = off, default dashboard, new dedicated dashboard, or url.
DASHBOARD_OFF = "none"
DASHBOARD_DEFAULT = "lovelace"
DASHBOARD_NEW = "__new__"
DASHBOARD_NEW_URL = "muj-cez"

PERIOD_DAILY = "daily"
PERIOD_WEEKLY = "weekly"
PERIOD_MONTHLY = "monthly"
UPDATE_PERIODS = [PERIOD_DAILY, PERIOD_WEEKLY, PERIOD_MONTHLY]

DEFAULT_UPDATE_PERIOD = PERIOD_DAILY
DEFAULT_UPDATE_TIME = "00:00:00"

# Retry a failed scheduled update this many times with this delay.
RETRY_COUNT = 6
RETRY_DELAY = timedelta(minutes=30)

# Storage of cached smart meter daily values (per config entry).
STORAGE_VERSION = 1

# HDO: refresh daily at this local time; regular updates refetch when older than this.
HDO_REFRESH_TIME = (0, 20)
HDO_MAX_AGE = timedelta(hours=6)
HDO_TIMEOUT = 90  # seconds for login and all signal requests
