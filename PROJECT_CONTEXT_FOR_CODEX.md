# Project Context For Codex

## 1. Overview

`visual-template-automation-toolkit` is a Python desktop automation toolkit based on visual template matching. It lets a user define image templates for visible UI elements, detect those templates on screen with OpenCV, and execute mouse/keyboard actions through PyAutoGUI.

The project is already adapted as a generic portfolio/demo version. It includes a fake CRM HTML page, fake CSV input files, PNG templates, and a JSON flow that fills the demo form. The public value of the project is that it demonstrates a reusable automation framework rather than a one-off RPA script.

Main user flow:

1. Start the Flet UI with `python main.py`.
2. Manage or test templates in the `Templates` view.
3. Open the demo target from the `Flows` view.
4. Run a JSON flow against CSV rows.
5. Inspect UI logs or failure screenshots if a template fails.

## 2. Stack And Tools

- Language: Python
- UI: Flet
- Computer vision: OpenCV and NumPy
- Desktop automation: PyAutoGUI
- Clipboard/text paste: pyperclip
- Screen capture: Pillow/ImageGrab
- Spreadsheet/CSV utilities: pandas and openpyxl
- Windows window focus helpers: pywin32

The project is primarily Windows-oriented because it uses `pywin32`, Windows screenshot shortcuts, and desktop mouse/keyboard automation.

## 3. How To Run Locally

Recommended setup:

```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

Run the JSON flow demo from the terminal:

```powershell
python flow_runner.py --open-target --limit 5
```

Run the simpler spreadsheet grouping demo:

```powershell
python reader.py
```

No environment variables are required.

## 4. Folder Structure

- `core.py`: visual automation engine, config loading, template matching, clicking, filling fields, listing templates, and window-focus helper methods.
- `flow_runner.py`: JSON flow executor. Loads a flow and CSV rows, resolves `{{field}}` placeholders, and dispatches actions.
- `interface.py`: Flet UI for template management, settings, demo flow execution, and log display.
- `reader.py`: small spreadsheet reader demo that validates required columns and groups rows into categories.
- `workflows.py`: placeholder/demo workflow dispatcher for grouped spreadsheet rows.
- `main.py`: entry point that starts the Flet UI.
- `config.json`: default runtime settings for confidence, extra delay, scale range, images directory, backup directory, and theme.
- `flows/demo_customer_form.json`: declarative demo flow.
- `examples/demo_target.html`: fake CRM target used by the visual automation demo.
- `examples/demo_customers.csv`: fake customer records used by the JSON flow.
- `examples/demo_items.csv`: fake rows used by the spreadsheet grouping demo.
- `examples/prints/`: public-safe cropped screenshots of the demo form.
- `assets/images/`: demo visual templates.
- `assets/backup/`: template backup folder; only `.gitkeep` should be committed.

## 5. Architecture

The project is split into three practical layers:

1. Automation engine: `VisualAutomation` in `core.py`.
2. Flow execution: `FlowRunner` in `flow_runner.py`.
3. User interface: Flet UI in `interface.py`.

`VisualAutomation` captures the current screen, searches for a template using `cv2.matchTemplate`, tests multiple scale values, returns an immutable `ImageMatch`, and performs PyAutoGUI actions based on the match.

`FlowRunner` reads a JSON flow and CSV rows. Each flow step has an `action` field and action-specific properties. Supported actions include `click_template`, `wait_template`, `fill_template`, `hotkey`, and `sleep`.

`interface.py` gives the user a visual way to manage templates, tune recognition settings, open the demo target, run flows, stop a running flow, and inspect logs. Long-running actions are launched in background threads so the UI does not freeze.

## 6. Main Flows

### Template Detection

Relevant files:

- `core.py`
- `interface.py`
- `assets/images/`

Steps:

1. The user clicks the test icon for a template in the UI.
2. `interface.py` calls `VisualAutomation.encontrar_imagem`.
3. `core.py` captures the screen and runs OpenCV template matching.
4. If a match passes the configured confidence threshold, the mouse moves to the match center and the UI shows the score.

### JSON Flow Runner

Relevant files:

- `flow_runner.py`
- `flows/demo_customer_form.json`
- `examples/demo_customers.csv`
- `core.py`

Steps:

1. `FlowRunner.load_flow` reads the JSON flow.
2. `FlowRunner.load_rows` reads CSV rows.
3. `FlowRunner.run_steps` loops through step actions.
4. Template-based actions call `VisualAutomation`.
5. If a step fails, `save_failure_screenshot` writes a screenshot under `logs/screenshots/`.

### Flet UI Flow Execution

Relevant files:

- `interface.py`
- `flow_runner.py`

Steps:

1. The user opens the `Flows` tab.
2. The user selects a flow JSON, CSV data file, and row limit.
3. `executar_fluxo` starts a background thread.
4. The thread creates a `FlowRunner` with a shared stop event.
5. Progress updates are sent back to the Flet UI.

## 7. Data Models And Structures

`ImageMatch` in `core.py`:

- `template_path`: path to the template image.
- `top_left`: top-left screen coordinate.
- `size`: matched template size after scaling.
- `score`: OpenCV match confidence score.
- `scale`: scale used for the best match.
- `center`: computed center coordinate.

JSON flow step examples:

- `click_template`: `template`, optional offsets and timeout.
- `wait_template`: `template`, optional timeout.
- `fill_template`: `template`, `value`, optional offsets, timeout, and final key.
- `hotkey`: `keys`.
- `sleep`: `seconds`.

CSV rows are loaded as dictionaries with `csv.DictReader`.

## 8. Integrations

No private APIs or external services are used.

The project interacts with:

- The local desktop screen through screenshots.
- The local mouse and keyboard through PyAutoGUI.
- The local clipboard through pyperclip.
- Browser-opened demo HTML through normal desktop automation, not through a browser API.

## 9. Important Modules

- `core.py`: most important technical module. Contains image matching, clicking, text filling, DPI check, and window focus helpers.
- `flow_runner.py`: strongest portfolio feature. Converts JSON + CSV into repeatable visual automation.
- `interface.py`: biggest module. Useful and demo-friendly, but concentrated in one large function.
- `examples/demo_target.html`: important because it lets the project be demonstrated without proprietary targets.
- `flows/demo_customer_form.json`: important because it proves the automation can be declared rather than hardcoded.

## 10. Current State

Complete:

- Visual matching engine.
- Template management UI.
- Configurable confidence and scale range.
- Demo target, templates, CSV input, and JSON flow.
- Failure screenshots for broken flow steps.
- Basic stop-event support for flow execution.

Needs improvement:

- `interface.py` is large and would benefit from splitting into smaller UI modules.
- JSON flows do not currently have formal schema validation.
- There are no automated tests.
- The project should be manually tested in a clean virtual environment before publication.
- Full automation tests should be run manually because PyAutoGUI controls the real desktop.

## 11. Tests

No automated tests are present.

Safe validation that does not move the mouse:

```powershell
python -m compileall -q .
```

Manual validation that controls mouse/keyboard:

```powershell
python flow_runner.py --open-target --limit 2
```

Keep the demo browser page visible and do not use the computer while the flow runs.

## 12. Sensitive Points

No company names, customer names, internal endpoints, credentials, tokens, passwords, or private URLs were found in the public demo files.

The demo contains fake CRM/customer terminology, including a `company` field in `examples/demo_customers.csv` and `examples/demo_target.html`. This appears generic and safe.

Generated runtime files should not be committed:

- `.venv/`
- `venv/`
- `env/`
- `__pycache__/`
- `*.pyc`
- `logs/`
- `*.log`
- `.env`
- `assets/backup/*`, except `assets/backup/.gitkeep`

## 13. Portfolio Adaptation Suggestions

Recommended next steps:

1. Test dependency installation in a clean virtual environment.
2. Run the demo flow with a small row limit.
3. Add a GIF of the demo flow if video documentation is desired.
4. Add automated tests for `FlowRunner.resolve_value`, `resolve_path`, `template_path`, and CSV/flow loading.
5. Add JSON schema validation for flow files.
6. Split `interface.py` into smaller modules if the project will be expanded.

## 14. Summary For Codex

If you modify this project, start here:

1. `flow_runner.py`: flow execution behavior and action dispatch.
2. `core.py`: template matching and PyAutoGUI interactions.
3. `interface.py`: UI wiring and demo runner.
4. `flows/demo_customer_form.json`: example of supported flow syntax.
5. `README.md`: public positioning and usage instructions.

Avoid running full flow tests automatically unless the user is ready for mouse and keyboard automation.
