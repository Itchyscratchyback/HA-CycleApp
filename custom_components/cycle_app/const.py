"""Constants for the Cycle App integration."""

DOMAIN = "cycle_app"

PLATFORMS = ["sensor", "button", "select", "number", "text"]

STORAGE_KEY = "cycle_app.data"
STORAGE_VERSION = 1

# Legacy files written by the old YAML package + save_history service.
LEGACY_PERIOD_FILE = "data/ha_cycle_app/period_start_history.json"
LEGACY_INTERCOURSE_FILE = "data/ha_cycle_app/intercourse_history.json"

# input_text max length was 255 characters; 23 ISO dates joined by commas fit.
MAX_PERIOD_DATES = 23

DEFAULT_CYCLE_LENGTH = 28
DEFAULT_LUTEAL_LENGTH = 14
MIN_CYCLE_LENGTH = 15
MAX_CYCLE_LENGTH = 60
MAX_CYCLE_SAMPLES = 24

NOT_SELECTED = "Not selected"

# key -> (name, options)
SELECTS = {
    "intercourse_type": (
        "Intercourse Type",
        [NOT_SELECTED, "Together", "F2M", "M2F"],
    ),
    "intercourse_subtype1": (
        "Intercourse How",
        [NOT_SELECTED, "Blowjob", "Handjob", "Creamfilljob", "Oystercleaning"],
    ),
    "intercourse_subtype2": (
        "Intercourse Execution",
        [NOT_SELECTED, "Full", "Quick"],
    ),
    "intercourse_raw": (
        "Intercourse RAW",
        [NOT_SELECTED, "Yes", "No", "Partially"],
    ),
    "intercourse_creampie": (
        "Intercourse Creampie",
        [NOT_SELECTED, "Yes", "No", "Partially"],
    ),
}
