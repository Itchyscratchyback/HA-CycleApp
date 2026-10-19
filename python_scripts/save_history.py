# Save a string to a file under the Home Assistant config directory
# Expects data: {'filename': 'path/within/config.json', 'content': '...'}
# Example call: hass.services.call('python_script','save_history', {'filename':'www/data/intercourse_history.json', 'content': states('input_text.intercourse_history')})

filename = data.get('filename')
content = data.get('content', '')
as_json = data.get('as_json', True)
append = data.get('append', False)

if not filename:
    logger.error('save_history: no filename provided')
else:
    path = hass.config.path(filename)
    dirpath = '/'.join(path.split('/')[:-1])
    try:
        import os, json, datetime
        if not os.path.exists(dirpath):
            os.makedirs(dirpath, exist_ok=True)
        payload = {
            'content': content,
            'updated_at': datetime.datetime.utcnow().isoformat() + 'Z',
            'length': len(content or '')
        }
        if append:
            # Append as ndjson (one JSON object per line) to preserve history
            if as_json:
                with open(path, 'a', encoding='utf-8') as f:
                    f.write(json.dumps(payload, ensure_ascii=False) + '\n')
                logger.info('save_history: appended JSON entry to %s', path)
            else:
                with open(path, 'a', encoding='utf-8') as f:
                    f.write(content + '\n')
                logger.info('save_history: appended raw entry to %s', path)
        else:
            if as_json:
                with open(path, 'w', encoding='utf-8') as f:
                    json.dump(payload, f, ensure_ascii=False, indent=2)
                logger.info('save_history: wrote JSON %s bytes to %s', os.path.getsize(path), path)
            else:
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(content)
                logger.info('save_history: wrote %s bytes to %s', len(content), path)
    except Exception as e:
        logger.exception('save_history: failed to write %s: %s', path, e)
