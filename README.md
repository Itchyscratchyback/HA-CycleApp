# Cycle App for Home Assistant

Cycle tracking, ovulation/fertility predictions and intercourse logging as a native Home Assistant integration. No YAML packages, helpers or automations are needed.

## Install (HACS)

1. HACS → ⋮ → **Custom repositories** → add `https://github.com/Itchyscratchyback/HA-CycleApp` as type **Integration**.
2. Download **Cycle App**, restart Home Assistant.
3. **Settings → Devices & services → Add integration → Cycle App**.

Updates arrive through HACS whenever a new GitHub release/tag is published.

## Entities

- `button.period_started`, `button.log_intercourse`, `button.clear_intercourse_history`
- `select.intercourse_type`, `_subtype1`, `_subtype2`, `_raw`, `_creampie`
- `number.luteal_length`
- `text.period_start_history` (editable, comma-separated `YYYY-MM-DD`), `text.intercourse_history`
- All `sensor.*` cycle/prediction/intercourse sensors (same entity IDs as the old YAML package)

Services: `cycle_app.add_period_start`, `cycle_app.remove_period_start`.

Data is stored in `.storage/cycle_app.data`.

## Migrating from the old YAML package

1. Remove the `cycleapp.yaml` package include (and its `input_*` helpers/automations) and restart.
2. Add the integration. Existing `data/ha_cycle_app/*.json` history is imported automatically on first start.
3. Dashboards are in `dashboards/`; they use the new `button.`, `select.`, `number.` and `text.` entity IDs.
