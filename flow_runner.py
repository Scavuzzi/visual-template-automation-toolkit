import argparse
import csv
import json
import time
import webbrowser
from datetime import datetime
from pathlib import Path

import pyautogui

from core import VisualAutomation


ROOT = Path(__file__).resolve().parent


class FlowRunner:
    """Executes visual automation flows described as JSON step lists."""

    def __init__(self, automation=None, base_dir: Path = ROOT, stop_event=None, progress_callback=None):
        self.automation = automation or VisualAutomation()
        self.base_dir = Path(base_dir)
        self.stop_event = stop_event
        self.progress_callback = progress_callback

    def run_flow_for_rows(self, flow_path: str | Path, data_path: str | Path, limit: int | None = None):
        flow = self.load_flow(flow_path)
        rows = self.load_rows(data_path)

        if limit is not None:
            rows = rows[:limit]

        print(f"Loaded flow: {flow.get('name', flow_path)}")
        print(f"Rows to process: {len(rows)}")

        for index, row in enumerate(rows, start=1):
            self.check_stop()
            print("=" * 40)
            print(f"RUNNING ROW {index}: {row}")
            self.report_progress(index, len(rows), "row_started", row)
            self.run_steps(flow["steps"], row)
            self.report_progress(index, len(rows), "row_finished", row)

    def load_flow(self, flow_path: str | Path):
        path = self.resolve_path(flow_path)
        with path.open("r", encoding="utf-8") as file:
            return json.load(file)

    def load_rows(self, data_path: str | Path):
        path = self.resolve_path(data_path)
        with path.open("r", encoding="utf-8", newline="") as file:
            return list(csv.DictReader(file))

    def run_steps(self, steps: list[dict], row: dict):
        for step_index, step in enumerate(steps, start=1):
            self.check_stop()
            action = step["action"]
            self.report_progress(None, None, f"step_{step_index}:{action}", row)

            match action:
                case "click_template":
                    self.click_template(step)
                case "wait_template":
                    self.wait_template(step)
                case "fill_template":
                    self.fill_template(step, row)
                case "hotkey":
                    pyautogui.hotkey(*step["keys"])
                case "sleep":
                    time.sleep(float(step.get("seconds", 1)))
                case _:
                    raise ValueError(f"Unknown flow action: {action}")

    def check_stop(self):
        if self.stop_event and self.stop_event.is_set():
            raise InterruptedError("Flow interrupted by user.")

    def report_progress(self, row_index, total_rows, status, row):
        if self.progress_callback:
            self.progress_callback(row_index, total_rows, status, row)

    def click_template(self, step: dict):
        template = self.template_path(step["template"])
        ok = self.automation.encontrar_e_clicar(
            template,
            offset_x=int(step.get("offset_x", 0)),
            offset_y=int(step.get("offset_y", 0)),
            timeout=float(step.get("timeout", 10)),
        )
        if not ok:
            self.save_failure_screenshot(f"click_{template.stem}")
            raise RuntimeError(f"Could not click template: {template.name}")

    def wait_template(self, step: dict):
        template = self.template_path(step["template"])
        match = self.automation.aguardar_imagem(template, timeout=float(step.get("timeout", 10)))
        if not match:
            self.save_failure_screenshot(f"wait_{template.stem}")
            raise RuntimeError(f"Could not find template: {template.name}")

    def fill_template(self, step: dict, row: dict):
        template = self.template_path(step["template"])
        value = self.resolve_value(step["value"], row)
        ok = self.automation.preencher_campo(
            template,
            value,
            offset_x=int(step.get("offset_x", 0)),
            offset_y=int(step.get("offset_y", 0)),
            timeout=float(step.get("timeout", 10)),
            tecla_final=step.get("final_key"),
        )
        if not ok:
            self.save_failure_screenshot(f"fill_{template.stem}")
            raise RuntimeError(f"Could not fill field near template: {template.name}")

    def resolve_value(self, value, row: dict):
        if isinstance(value, str) and value.startswith("{{") and value.endswith("}}"):
            key = value[2:-2].strip()
            return row.get(key, "")
        return value

    def template_path(self, template_name: str):
        return self.base_dir / "assets" / "images" / template_name

    def resolve_path(self, path: str | Path):
        path = Path(path)
        if path.is_absolute():
            return path
        return self.base_dir / path

    def save_failure_screenshot(self, label: str):
        screenshots_dir = self.base_dir / "logs" / "screenshots"
        screenshots_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_label = "".join(char if char.isalnum() or char in "-_" else "_" for char in label)
        path = screenshots_dir / f"{timestamp}_{safe_label}.png"
        pyautogui.screenshot().save(path)
        print(f"Failure screenshot saved: {path}")


def main():
    parser = argparse.ArgumentParser(description="Run a visual template automation flow.")
    parser.add_argument("--flow", default="flows/demo_customer_form.json")
    parser.add_argument("--data", default="examples/demo_customers.csv")
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--open-target", action="store_true")
    parser.add_argument("--startup-delay", type=float, default=2.0)
    args = parser.parse_args()

    if args.open_target:
        webbrowser.open((ROOT / "examples" / "demo_target.html").resolve().as_uri())
        time.sleep(args.startup_delay)

    FlowRunner().run_flow_for_rows(args.flow, args.data, args.limit)


if __name__ == "__main__":
    main()
