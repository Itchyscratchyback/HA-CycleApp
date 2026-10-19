# Load a string from a file under the Home Assistant config directory and set it to an input_text entity
# Expects data: {'filename': 'path/within/config.json', 'entity_id': 'input_text.intercourse_history'}

filename = data.get('filename')
entity_id = data.get('entity_id')

if not filename or not entity_id:
    logger.error('load_history: filename or entity_id missing')
else:
    path = hass.config.path(filename)
    try:
        import json
        with open(path, 'r', encoding='utf-8') as f:
            raw = f.read()
        content = ''
        # If file looks like NDJSON (multiple JSON objects per line), parse each line
        lines = [l.strip() for l in raw.splitlines() if l.strip()]
        if len(lines) > 1:
            parts = []
            for line in lines:
                try:
                    obj = json.loads(line)
                    parts.append(obj.get('content', ''))
                except Exception:
                    parts.append(line)
            content = ','.join([p for p in parts if p])
        else:
            # Single-line: try to parse full JSON object
            try:
                obj = json.loads(raw)
                content = obj.get('content', raw)
            except Exception:
                content = raw

        hass.services.call('input_text', 'set_value', {'entity_id': entity_id, 'value': content})
        logger.info('load_history: loaded %s bytes into %s', len(content), entity_id)
    except FileNotFoundError:
        logger.warning('load_history: file not found %s', path)
    except Exception as e:
        logger.exception('load_history: failed to load %s: %s', path, e)
