# Redaction And Portfolio Plan

## 1. Sensitive Data Inventory

No sensitive business data was found in the current public demo version.

Checked categories:

- Company/client names: none found beyond generic fake CRM terminology.
- People names: fake demo names only.
- Emails: fake demo emails only.
- Internal domains/endpoints: none found.
- API keys/tokens/secrets: none found.
- Credentials: none found.
- Proprietary workflow names: none found.
- Private application screenshots/templates: none found in the current demo assets.

The term `company` appears as a generic demo form field and CSV column. It is safe for a public demo.

## 2. Files That Should Not Be Published

The repository should not include generated or local runtime files:

- `.venv/`
- `venv/`
- `env/`
- `__pycache__/`
- `*.pyc`
- `logs/`
- `*.log`
- `.env`
- `assets/backup/*`, except `assets/backup/.gitkeep`

The existing `.gitignore` already covers these items.

## 3. Current Public-Safe Assets

These files look safe to keep:

- `examples/demo_target.html`
- `examples/demo_customers.csv`
- `examples/demo_items.csv`
- `examples/prints/demo-form-empty.png`
- `examples/prints/demo-form-filled.png`
- `examples/prints/demo-form-saved.png`
- `flows/demo_customer_form.json`
- `assets/images/demo_*.png`
- `README.md`
- `LICENSE`
- Source files in the project root

The demo is intentionally generic and does not reveal a production target system.

## 4. Portfolio Positioning

Recommended public description:

> A Python toolkit for building visual desktop automations using OpenCV template matching, PyAutoGUI actions, a Flet template-management UI, and JSON/CSV-driven workflows.

Strong points to highlight:

- Reusable computer-vision automation core.
- Declarative flow execution through JSON.
- CSV-driven batch automation.
- Local demo target with fake data.
- Failure screenshots for debugging.
- Configurable recognition confidence and scale range.

## 5. Manual Review Checklist Before GitHub

Before publishing:

1. Run a final search for sensitive terms:

```powershell
rg -n "token|secret|password|senha|cliente|client|internal|private|empresa|companyname|http://" .
```

2. Confirm no production templates were copied into `assets/images/`.
3. Confirm no runtime screenshots exist under `logs/`.
4. Confirm no virtual environment is inside the repo.
5. Confirm `assets/backup/` contains only `.gitkeep`.
6. Run a clean install in a virtual environment.
7. Run the demo manually with a small limit.

## 6. Technical Improvements For Portfolio

High priority:

- Add a GIF of the demo flow running if video documentation is desired.
- Add automated tests for pure logic in `flow_runner.py`.
- Add flow schema validation so invalid JSON produces friendly errors.

Medium priority:

- Split `interface.py` into smaller modules.
- Make `reader.py` and `workflows.py` more clearly labeled as examples.
- Add a richer sample flow with optional `final_key`, offsets, and delays.
- Add a troubleshooting section for template matching failures.

Low priority:

- Package the project as an installable CLI.
- Add support for YAML flows.
- Add per-step confidence overrides.

## 7. Legal And Safety Notes

This project controls the local desktop. It should include a clear warning that running flows can move the mouse, paste text, and trigger keyboard shortcuts.

There are no obvious licensing problems in the code. The repository includes an MIT license.

The project should not be presented as a bot for bypassing systems or policies. Frame it as a local desktop automation toolkit for repetitive UI tasks and testing/demo workflows.

## 8. Recommended Publication Steps

1. Keep the current generic demo assets.
2. Add screenshots or a short GIF.
3. Run safe syntax validation:

```powershell
python -m compileall -q .
```

4. Run manual desktop automation validation:

```powershell
python flow_runner.py --open-target --limit 2
```

5. Commit only source, demo files, documentation, and static demo assets.

## 9. Summary

This project is low risk for redaction and high value for portfolio use. It is already generic, includes fake data, and demonstrates a reusable approach to visual desktop automation.
