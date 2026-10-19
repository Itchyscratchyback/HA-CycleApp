from datetime import datetime
import os, json

# pyscript services: call via service: pyscript.save_history
@service
def save_history(filename=None, content='', as_json=True, append=False):
    if not filename:
        log.error('save_history: no filename provided')
        return
    try:
        path = hass.config.path(filename)
        dirpath = os.path.dirname(path)
        if not os.path.exists(dirpath):
            os.makedirs(dirpath, exist_ok=True)
        payload = {
            'content': content,
            'updated_at': datetime.utcnow().isoformat() + 'Z',
            'length': len(content or '')
        }
        if append:
            if as_json:
                with open(path, 'a', encoding='utf-8') as f:
                    f.write(json.dumps(payload, ensure_ascii=False) + '\n')
                log.info('save_history: appended JSON entry to %s', path)
            else:
                with open(path, 'a', encoding='utf-8') as f:
                    f.write(content + '\n')
                log.info('save_history: appended raw entry to %s', path)
        else:
            if as_json:
                with open(path, 'w', encoding='utf-8') as f:
                    json.dump(payload, f, ensure_ascii=False, indent=2)
                log.info('save_history: wrote JSON to %s', path)
            else:
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(content)
                log.info('save_history: wrote raw to %s', path)
    except Exception as e:
        log.exception('save_history: failed to write %s: %s', filename, e)


@service
def load_history(filename=None, entity_id=None):
    if not filename or not entity_id:
        log.error('load_history: filename or entity_id missing')
        return
    try:
        path = hass.config.path(filename)
        with open(path, 'r', encoding='utf-8') as f:
            raw = f.read()
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
            try:
                obj = json.loads(raw)
                content = obj.get('content', raw)
            except Exception:
                content = raw
        hass.services.call('input_text', 'set_value', {'entity_id': entity_id, 'value': content})
        log.info('load_history: loaded into %s', entity_id)
    except FileNotFoundError:
        log.warning('load_history: file not found %s', filename)
    except Exception as e:
        log.exception('load_history: failed to load %s: %s', filename, e)
