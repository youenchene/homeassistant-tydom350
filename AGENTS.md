# Agent guidance

These instructions apply to the whole repository.

## Project

This is a Home Assistant custom integration for the legacy Delta Dore TYDOM
350 PC. It reads the gateway's French HTML pages and sends local CGI commands.
Do not confuse this protocol with the WebSocket API of modern Tydom gateways.
Read `README.md` before changing supported behavior or installation steps.

## Code layout

- `custom_components/tydom350/protocol.py`: HTML parsing and command extraction;
  keep it independent of Home Assistant and network access.
- `api.py`: asynchronous HTTP transport, serialization, and command allow-list.
- `__init__.py`: coordinator and integration lifecycle.
- `config_flow.py`: configuration and read-only connection validation.
- `entity.py`, `light.py`, `select.py`, `sensor.py`: Home Assistant entities.
- `strings.json` and `translations/fr.json`: configuration UI text.
- `tests/fixtures/`: synthetic gateway pages, including malformed HTML.
- `tests/test_protocol.py` and `tests/test_runtime.py`: parser, transport, and
  entity behavior tests.

## Protocol and entity rules

- `COUNT` is a changing page token, not an operation code. Fetch the appropriate
  page immediately before sending a command, under the same client lock.
- Keep gateway requests sequential, bounded by timeouts, and asynchronous.
  Do not automatically retry or replay commands, including through redirects.
- Accept only known local CGI paths and explicitly supported parameters.
  Do not extend control to reset, alarm, pairing, credentials, or network
  configuration as an incidental part of another change.
- Treat missing or unreadable measurements as unknown or unavailable, not zero.
- Light state is assumed from the last successful Home Assistant command; it is
  not verified physical feedback. Preserve the unknown initial state and explain
  this limitation in user-facing documentation.
- Heating zones offer Eco/Comfort modes. Stop/Automatic controls are global.
  Do not invent per-zone stop commands or temperature setpoints.
- Preserve consumption units. EUR is monetary data, not energy; never infer
  kWh from it. An HTTP success does not confirm radio reception.
- Preserve existing entity unique IDs unless a deliberate migration is needed.
- Keep configuration validation read-only and avoid blocking I/O in the event
  loop. Keep UI strings and the French translation consistent.

## Tests

Use Python 3.14 and the pinned test dependencies:

```sh
uv venv --python 3.14
uv pip install --python .venv/bin/python -r requirements-test.txt
.venv/bin/python -m pytest -q
```

Reuse an existing virtual environment when available. For code changes, run
the suite and add focused regression coverage for changed behavior, especially
parsing, command scope, tokens, units, and error handling. Tests must use
synthetic fixtures or the simulated local HTTP server, never a real gateway.
For documentation-only edits, check the diff; no test run is required.

## Publication and live installations

- Keep real gateway captures, credentials, private network addresses, household
  names, consumption readings, and screenshots out of commits. Use fictional
  values in fixtures and examples. `research/` and `dist/` are intentionally
  ignored; do not force-add their contents.
- Repository changes do not automatically authorize deployment, Home Assistant
  restarts, or physical device commands. Keep live work within the user's
  requested scope and report separately what was simulated and what was
  verified on hardware.
- Update `README.md` when supported behavior or installation changes. Update
  `manifest.json` when intentionally preparing a new integration version.
- Before committing, inspect staged files and run `git diff --cached --check`.
  Keep commits focused and avoid unrelated modifications.
