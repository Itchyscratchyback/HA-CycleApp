"""Cycle App custom component providing simple persistence services.

Services provided:
- cycle_app.save_history: filename, content, as_json=True, append=False
- cycle_app.load_history: filename, entity_id

Files are stored under the Home Assistant config directory using hass.config.path(filename).
"""
import logging
import os
import json
import datetime

_LOGGER = logging.getLogger(__name__)
from .const import DOMAIN


def _write(path, content, as_json=True, append=False):
    dirpath = os.path.dirname(path)
    if not os.path.exists(dirpath):
        os.makedirs(dirpath, exist_ok=True)
    payload = {
        "content": content,
        "updated_at": datetime.datetime.utcnow().isoformat() + "Z",
        "length": len(content or "")
    }
    if append:
        if as_json:
            with open(path, "a", encoding="utf-8") as f:
                f.write(json.dumps(payload, ensure_ascii=False) + "\n")
        else:
            with open(path, "a", encoding="utf-8") as f:
                f.write(content + "\n")
    else:
        if as_json:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
        else:
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)


def _read(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            raw = f.read()
    except FileNotFoundError:
        return None
    lines = [l.strip() for l in raw.splitlines() if l.strip()]
    if len(lines) > 1:
        parts = []
        for line in lines:
            try:
                obj = json.loads(line)
                parts.append(obj.get("content", ""))
            except Exception:
                parts.append(line)
        return ",".join([p for p in parts if p])
    else:
        try:
            obj = json.loads(raw)
            return obj.get("content", raw)
        except Exception:
            return raw


def async_setup(hass, config):
    """Set up the cycle_app component.

    This component uses config entries; nothing to do at YAML setup time.
    Returning True allows the integration to be configured via the UI.
    """
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_setup_entry(hass, entry):
    """Set up a config entry and register services."""

    def handle_save(call):
        filename = call.data.get("filename")
        content = call.data.get("content", "")
        as_json = call.data.get("as_json", True)
        append = call.data.get("append", False)
        if not filename:
            _LOGGER.error("save_history: no filename provided")
            return
        path = hass.config.path(filename)
        try:
            _write(path, content, as_json=as_json, append=append)
            _LOGGER.info("save_history: wrote %s (append=%s)", path, append)
        except Exception as e:
            _LOGGER.exception("save_history: failed to write %s: %s", path, e)

    def handle_load(call):
        filename = call.data.get("filename")
        entity_id = call.data.get("entity_id")
        if not filename or not entity_id:
            _LOGGER.error("load_history: filename or entity_id missing")
            return
        path = hass.config.path(filename)
        content = _read(path)
        if content is None:
            _LOGGER.warning("load_history: file not found %s", path)
            return
        hass.services.call("input_text", "set_value", {"entity_id": entity_id, "value": content})
        _LOGGER.info("load_history: loaded into %s", entity_id)

    hass.services.register(DOMAIN, "save_history", handle_save)
    hass.services.register(DOMAIN, "load_history", handle_load)
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = True
    return True


async def async_unload_entry(hass, entry):
    """Unload a config entry and remove services."""
    try:
        hass.services.async_remove(DOMAIN, "save_history")
        hass.services.async_remove(DOMAIN, "load_history")
    except Exception:
        _LOGGER.exception("Error removing services for %s", entry.entry_id)
    hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
    return True
