import base64
import logging
import shutil
import threading
import time
import webbrowser
from pathlib import Path

import flet as ft
import pyautogui

from core import DEFAULT_CONFIG, VisualAutomation, load_config, save_config
from flow_runner import FlowRunner, ROOT


CONFIG_FILE = "config.json" # Caminho para o arquivo de configuração da aplicação
LOG_DIR = Path("logs") # Diretório onde os arquivos de log serão armazenados
LOG_DIR.mkdir(exist_ok=True) # Garante que o diretório de logs exista, criando-o se necessário

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "base_visual.log", encoding="utf-8", mode="a"),
        logging.StreamHandler(),
    ],
    force=True,
)


def _ensure_dirs(cfg: dict) -> tuple[Path, Path]:
    """
    Garante que os diretórios para imagens e backup existam, criando-os se necessário, e retorna os objetos Path correspondentes.

    :param cfg: Dicionário de configuração contendo os caminhos dos diretórios (opcional, se não fornecido, serão usados os valores padrão).
    :returns: Tupla contendo os objetos Path para os diretórios de imagens e backup, respectivamente.
    """


    images_dir = Path(cfg.get("images_dir", DEFAULT_CONFIG["images_dir"]))
    backup_dir = Path(cfg.get("backup_dir", DEFAULT_CONFIG["backup_dir"]))
    images_dir.mkdir(parents=True, exist_ok=True)
    backup_dir.mkdir(parents=True, exist_ok=True)
    return images_dir, backup_dir


def _image_to_base64(path: Path) -> str:
    """
    Converte uma imagem em um arquivo para uma string codificada em base64, que pode ser usada para exibir a imagem em um widget de interface gráfica.

    :param path: Objeto Path representando o caminho para o arquivo de imagem a ser convertido.
    :returns: String contendo a representação em base64 da imagem, decodificada para UTF-8 para ser usada em componentes de interface gráfica que aceitam imagens em formato base64.
    """
    with path.open("rb") as file:
        return base64.b64encode(file.read()).decode("utf-8")


def main(page: ft.Page):
    """
    Função principal que configura e exibe a interface gráfica da aplicação usando Flet. A função carrega as configurações, garante que os diretórios necessários existam, inicializa a automação visual, e define os componentes da interface, incluindo a lógica para interações do usuário como adicionar, testar, substituir, capturar e excluir templates de imagem, bem como ajustar as configurações de reconhecimento de imagem e alternar entre temas claro e escuro.

    :param page: Objeto Page do Flet que representa a janela principal da aplicação onde os componentes da interface serão adicionados e atualizados.
    """
    cfg = load_config(CONFIG_FILE)
    images_dir, backup_dir = _ensure_dirs(cfg)
    automacao = VisualAutomation(CONFIG_FILE)
    root_dir = ROOT

    page.title = "Visual Template Automation Toolkit"
    page.window_width = 1000
    page.window_height = 680
    page.theme_mode = ft.ThemeMode.DARK if cfg.get("theme_mode") == "dark" else ft.ThemeMode.LIGHT

    file_picker = ft.FilePicker()
    page.overlay.append(file_picker)

    log_list = ft.ListView(expand=True, spacing=4, auto_scroll=True)
    status_text = ft.Text("Ready", size=12)
    grid_view = ft.GridView(expand=True, max_extent=300, spacing=10, run_spacing=10, padding=10)

    def run_on_ui_thread(callback):
        call_from_thread = getattr(page, "call_from_thread", None)
        if callable(call_from_thread):
            call_from_thread(callback)
        else:
            callback()

    class UILogHandler(logging.Handler):
        """
        Manipulador de log personalizado para exibir mensagens de log na interface do usuario do Flet.
        """

        def emit(self, record):
            """
            Processa um registro de log, formatando a mensagem e adicionando-a à ListView de logs na interface do usuário. A atualização da interface é feita de forma thread-safe para garantir que as mensagens sejam exibidas corretamente mesmo quando os logs são gerados a partir de threads diferentes.
            """
            msg = self.format(record)

            def update_log():
                log_list.controls.append(ft.Text(msg, size=12))
                page.update()

            run_on_ui_thread(update_log)

    ui_handler = UILogHandler()
    ui_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
    logging.getLogger().addHandler(ui_handler)

    def set_status(texto: str):
        """
        Atualiza o texto de status exibido na interface do usuário com a mensagem fornecida.

        :param texto: String contendo a mensagem de status a ser exibida.
        """
        def update_status():
            status_text.value = texto
            page.update()

        run_on_ui_thread(update_status)

    def copiar_para_backup():
        """
        Copia os templates de imagem do diretório de imagens para o diretório de backup, primeiro limpando o diretório de backup para garantir que apenas os arquivos atuais sejam mantidos.
        """
        for arquivo in backup_dir.glob("*"):
            if arquivo.is_file():
                arquivo.unlink()

        for arquivo in images_dir.glob("*"):
            if arquivo.suffix.lower() in [".png", ".jpg", ".jpeg", ".bmp"]:
                shutil.copy2(arquivo, backup_dir / arquivo.name)

    def restaurar_backup(e=None):
        """
        Restaura os templates de imagem a partir do diretório de backup, copiando os arquivos de volta para o diretório de imagens e atualizando a visualização para refletir as mudanças.
        """
        for arquivo in backup_dir.glob("*"):
            if arquivo.suffix.lower() in [".png", ".jpg", ".jpeg", ".bmp"]:
                shutil.copy2(arquivo, images_dir / arquivo.name)

        carregar_imagens()
        set_status("Templates restored from backup.")

    def testar_imagem(img_path: Path, status_label: ft.Text):
        """
        Testa a detecção de um template de imagem na tela, atualizando o status_label com o resultado do teste. A função é executada em uma thread separada para evitar bloqueios na interface do usuário durante o processo de detecção.

        :param img_path: Objeto Path representando o arquivo de imagem do template a ser testado.
        :param status_label: Widget de texto do Flet onde o resultado do teste será exib
        """
        def worker():
            try:
                match = automacao.encontrar_imagem(img_path)
                if match:
                    x, y = match.center
                    pyautogui.moveTo(x, y, duration=0.2)
                    status_label.value = f"OK {match.score:.2f}"
                    status_label.color = ft.colors.GREEN
                else:
                    status_label.value = "Not found"
                    status_label.color = ft.colors.RED
                run_on_ui_thread(page.update)
            except Exception as exc:
                status_label.value = f"Error: {exc}"
                status_label.color = ft.colors.RED
                run_on_ui_thread(page.update)

        threading.Thread(target=worker, daemon=True).start()

    def substituir_template(target: Path):
        """
        Abre um diálogo de seleção de arquivos para o usuário escolher um novo template de imagem para substituir o template existente representado por 'target'. O arquivo selecionado é copiado para o local do template existente, substituindo-o, e a visualização é atualizada para refletir a mudança.

        :param target: Objeto Path representando o arquivo de template a ser substituído.
        """
        def on_result(ev: ft.FilePickerResultEvent):
            if ev.files:
                novo = Path(ev.files[0].path)
                shutil.copy2(novo, target)
                carregar_imagens()
                set_status(f"Template updated: {target.name}")

        file_picker.on_result = on_result
        file_picker.pick_files(
            allow_multiple=False,
            allowed_extensions=["png", "jpg", "jpeg", "bmp"],
        )

    def adicionar_templates(e=None):
        """
        Abre um diálogo de seleção de arquivos para o usuário escolher um ou mais templates de imagem para adicionar à base visual. Os arquivos selecionados são copiados para o diretório de imagens e a visualização é atualizada para refletir as novas adições.

        :param e: Evento de clique (opcional, não utilizado na função).
        """
        def on_result(ev: ft.FilePickerResultEvent):
            if ev.files:
                for item in ev.files:
                    origem = Path(item.path)
                    shutil.copy2(origem, images_dir / origem.name)
                carregar_imagens()
                set_status("Template(s) added.")

        file_picker.on_result = on_result
        file_picker.pick_files(
            allow_multiple=True,
            allowed_extensions=["png", "jpg", "jpeg", "bmp"],
        )

    def capturar_template(target: Path):
        """
        Inicia um processo de captura de tela, solicitando ao usuário que selecione uma área da tela para capturar, e salva a imagem resultante no caminho especificado por 'target'. A função é executada em uma thread separada para evitar bloqueios na interface do usuário durante o processo de captura.

        :param target: Objeto Path representando o arquivo de destino onde a captura de tela será salva.
        """
        def worker():

            try:
                from PIL import ImageGrab

                pyautogui.hotkey("win", "shift", "s")
                set_status("Select a screen area to capture.")

                img = None
                for _ in range(40):
                    img = ImageGrab.grabclipboard()
                    if img:
                        break
                    time.sleep(0.2)

                if img is None:
                    raise RuntimeError("Capture not found in clipboard.")

                img.save(target, format="PNG")
                carregar_imagens()
                set_status(f"Capture saved to {target.name}.")
            except Exception as exc:
                set_status(f"Capture error: {exc}")

        threading.Thread(target=worker, daemon=True).start()

    def excluir_template(target: Path):
        """
        Exclui o template de imagem selecionado, removendo o arquivo correspondente do sistema de arquivos e atualizando a visualização para refletir a remoção.

        :param target: Objeto Path representando o arquivo de template a ser excluído.
        """
        target.unlink(missing_ok=True)
        carregar_imagens()
        set_status(f"Template removed: {target.name}")

    def carregar_imagens():
        """
        Carrega os templates de imagem do diretório especificado, atualizando a visualização em grade com as miniaturas e opções de ação para cada template.
        """
        grid_view.controls.clear()
        arquivos = automacao.listar_templates(images_dir)

        if not arquivos:
            grid_view.controls.append(
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Icon(ft.icons.IMAGE_SEARCH, size=48),
                            ft.Text("No templates registered.", size=16, weight=ft.FontWeight.W_600),
                            ft.Text("Add or capture images from the target application to start mapping."),
                        ],
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=10,
                    ),
                    padding=20,
                    alignment=ft.alignment.center,
                )
            )
            page.update()
            return

        for img_file in arquivos:
            status_label = ft.Text("", size=12)
            img_widget = ft.Image(
                src_base64=_image_to_base64(img_file),
                height=150,
                fit=ft.ImageFit.CONTAIN,
            )

            grid_view.controls.append(
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Row(
                                [
                                    ft.Text(img_file.name, size=14, weight=ft.FontWeight.W_600, expand=True),
                                    ft.IconButton(
                                        icon=ft.icons.TOUCH_APP,
                                        tooltip="Test on screen",
                                        on_click=lambda e, path=img_file, label=status_label: testar_imagem(path, label),
                                    ),
                                ],
                                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            ),
                            img_widget,
                            status_label,
                            ft.Row(
                                [
                                    ft.IconButton(
                                        icon=ft.icons.UPLOAD_FILE,
                                        tooltip="Replace file",
                                        on_click=lambda e, path=img_file: substituir_template(path),
                                    ),
                                    ft.IconButton(
                                        icon=ft.icons.CAMERA_ALT,
                                        tooltip="Capture screen",
                                        on_click=lambda e, path=img_file: capturar_template(path),
                                    ),
                                    ft.IconButton(
                                        icon=ft.icons.DELETE_OUTLINE,
                                        tooltip="Delete template",
                                        on_click=lambda e, path=img_file: excluir_template(path),
                                    ),
                                ],
                                alignment=ft.MainAxisAlignment.CENTER,
                            ),
                        ],
                        spacing=8,
                    ),
                    border=ft.border.all(1, ft.colors.with_opacity(0.12, ft.colors.ON_SURFACE)),
                    border_radius=8,
                    padding=10,
                )
            )

        page.update()

    confidence_slider = ft.Slider(
        min=40,
        max=100,
        divisions=60,
        value=int(float(cfg.get("confidence", 0.8)) * 100),
        label="{value}%",
    )
    sleep_field = ft.TextField(
        label="Extra delay between actions (s)",
        value=str(cfg.get("sleep_extra", 0.0)),
        width=220,
    )
    escala_min_field = ft.TextField(
        label="Minimum scale",
        value=str(cfg.get("image_scale_min", 0.8)),
        width=160,
    )
    escala_max_field = ft.TextField(
        label="Maximum scale",
        value=str(cfg.get("image_scale_max", 1.2)),
        width=160,
    )
    flow_path_field = ft.TextField(
        label="Flow JSON",
        value="flows/demo_customer_form.json",
        expand=True,
    )
    data_path_field = ft.TextField(
        label="CSV data",
        value="examples/demo_customers.csv",
        expand=True,
    )
    limit_field = ft.TextField(
        label="Limit",
        value="5",
        width=120,
    )
    flow_running = {"value": False}
    flow_stop_event = threading.Event()
    flow_progress_text = ft.Text("No flow running.", size=12)

    def salvar_config(e=None):
        """
        Salva as configuracoes ajustadas pelo usuario, atualizando o arquivo de configuracao e recarregando as configuracoes na automacao visual.
        """
        try:
            cfg["confidence"] = float(confidence_slider.value) / 100
            cfg["sleep_extra"] = float(sleep_field.value)
            cfg["image_scale_min"] = float(escala_min_field.value)
            cfg["image_scale_max"] = float(escala_max_field.value)
            save_config(cfg, CONFIG_FILE)
            automacao.reload_config()
            set_status("Settings saved.")
        except Exception as exc:
            set_status(f"Error saving settings: {exc}")

    def alternar_tema(e=None):
        """
        Alterna entre os modos de tema claro e escuro, atualizando a configuração e a interface do usuário em conformidade.
        """

        cfg["theme_mode"] = "light" if cfg.get("theme_mode") == "dark" else "dark"
        save_config(cfg, CONFIG_FILE)
        page.theme_mode = ft.ThemeMode.DARK if cfg["theme_mode"] == "dark" else ft.ThemeMode.LIGHT
        page.update()

    def abrir_demo_target(e=None):
        target = root_dir / "examples" / "demo_target.html"
        webbrowser.open(target.resolve().as_uri())
        set_status("Demo target opened.")

    def escolher_arquivo(field: ft.TextField, allowed_extensions: list[str]):
        def on_result(ev: ft.FilePickerResultEvent):
            if ev.files:
                path = Path(ev.files[0].path)
                try:
                    field.value = str(path.relative_to(root_dir))
                except ValueError:
                    field.value = str(path)
                page.update()

        file_picker.on_result = on_result
        file_picker.pick_files(allow_multiple=False, allowed_extensions=allowed_extensions)

    def executar_fluxo(e=None):
        if flow_running["value"]:
            set_status("Flow already running.")
            return

        def on_progress(row_index, total_rows, status, row):
            def update_progress():
                if row_index and total_rows:
                    flow_progress_text.value = f"Row {row_index}/{total_rows}: {status}"
                else:
                    flow_progress_text.value = status
                page.update()

            run_on_ui_thread(update_progress)

        def worker():
            flow_running["value"] = True
            flow_stop_event.clear()
            set_status("Running flow...")

            try:
                limit_text = str(limit_field.value).strip()
                limit = int(limit_text) if limit_text else None

                runner = FlowRunner(
                    VisualAutomation(CONFIG_FILE, stop_event=flow_stop_event),
                    root_dir,
                    stop_event=flow_stop_event,
                    progress_callback=on_progress,
                )
                flow = runner.load_flow(flow_path_field.value)
                rows = runner.load_rows(data_path_field.value)
                if limit is not None:
                    rows = rows[:limit]

                logging.info("Loaded flow: %s", flow.get("name", flow_path_field.value))
                logging.info("Rows to process: %s", len(rows))

                for index, row in enumerate(rows, start=1):
                    logging.info("Running row %s/%s: %s", index, len(rows), row)
                    on_progress(index, len(rows), "row_started", row)
                    runner.run_steps(flow["steps"], row)
                    logging.info("Row %s completed.", index)
                    on_progress(index, len(rows), "row_finished", row)

                set_status("Flow finished.")
            except InterruptedError:
                logging.warning("Flow stopped by user.")
                set_status("Flow stopped.")
            except Exception as exc:
                logging.exception("Flow failed: %s", exc)
                set_status(f"Flow failed: {exc}")
            finally:
                flow_running["value"] = False

        threading.Thread(target=worker, daemon=True).start()

    def parar_fluxo(e=None):
        flow_stop_event.set()
        set_status("Stop requested.")

    templates_view = ft.Column(
        [
            ft.Row(
                [
                    ft.Text("Visual Templates", size=20, weight=ft.FontWeight.W_600),
                    ft.Row(
                        [
                            ft.IconButton(ft.icons.CREATE_NEW_FOLDER, tooltip="Add templates", on_click=adicionar_templates),
                            ft.IconButton(ft.icons.FOLDER_OPEN, tooltip="Open folder", on_click=lambda e: webbrowser.open(str(images_dir.resolve()))),
                            ft.IconButton(ft.icons.SAVE, tooltip="Save backup", on_click=lambda e: (copiar_para_backup(), set_status("Backup updated."))),
                            ft.IconButton(ft.icons.RESTORE, tooltip="Restore backup", on_click=restaurar_backup),
                            ft.IconButton(ft.icons.REFRESH, tooltip="Refresh", on_click=lambda e: carregar_imagens()),
                        ],
                        spacing=4,
                    ),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            ),
            grid_view,
        ],
        expand=True,
    )

    config_view = ft.Column(
        [
            ft.Text("Settings", size=20, weight=ft.FontWeight.W_600),
            ft.Text("Image recognition confidence level."),
            confidence_slider,
            ft.Row([sleep_field, escala_min_field, escala_max_field], spacing=12),
            ft.FilledButton("Save", icon=ft.icons.SAVE, on_click=salvar_config),
        ],
        spacing=16,
        expand=True,
    )

    flows_view = ft.Column(
        [
            ft.Text("Demo Flow Runner", size=20, weight=ft.FontWeight.W_600),
            ft.Row(
                [
                    ft.FilledButton("Open demo target", icon=ft.icons.OPEN_IN_BROWSER, on_click=abrir_demo_target),
                    ft.FilledButton("Run flow", icon=ft.icons.PLAY_ARROW, on_click=executar_fluxo),
                    ft.FilledTonalButton("Stop flow", icon=ft.icons.STOP, on_click=parar_fluxo),
                ],
                spacing=10,
            ),
            ft.Row(
                [
                    flow_path_field,
                    ft.IconButton(
                        icon=ft.icons.FOLDER_OPEN,
                        tooltip="Choose flow JSON",
                        on_click=lambda e: escolher_arquivo(flow_path_field, ["json"]),
                    ),
                ],
                spacing=8,
            ),
            ft.Row(
                [
                    data_path_field,
                    ft.IconButton(
                        icon=ft.icons.FOLDER_OPEN,
                        tooltip="Choose CSV data",
                        on_click=lambda e: escolher_arquivo(data_path_field, ["csv"]),
                    ),
                    limit_field,
                ],
                spacing=8,
            ),
            flow_progress_text,
            ft.Text("Open the demo target, keep it visible, then run the flow."),
        ],
        spacing=16,
        expand=True,
    )

    logs_view = ft.Column(
        [
            ft.Text("Logs", size=20, weight=ft.FontWeight.W_600),
            ft.Container(
                content=log_list,
                expand=True,
                padding=10,
                border=ft.border.all(1, ft.colors.with_opacity(0.12, ft.colors.ON_SURFACE)),
                border_radius=8,
            ),
        ],
        expand=True,
    )

    content = ft.Container(expand=True)

    def set_view(index: int):
        """
        Atualiza a visualizacao principal com base no indice selecionado na NavigationRail.

        :param index: Indice da visualizacao a ser exibida (0 para templates, 1 para configuracoes, 2 para logs).
        """
        content.content = [templates_view, config_view, flows_view, logs_view][index]
        page.update()

    nav = ft.NavigationRail(
        selected_index=0,
        label_type=ft.NavigationRailLabelType.ALL,
        destinations=[
            ft.NavigationRailDestination(icon=ft.icons.IMAGE_SEARCH, label="Templates"),
            ft.NavigationRailDestination(icon=ft.icons.TUNE, label="Config"),
            ft.NavigationRailDestination(icon=ft.icons.PLAY_ARROW, label="Flows"),
            ft.NavigationRailDestination(icon=ft.icons.SUBJECT, label="Logs"),
        ],
        on_change=lambda e: set_view(e.control.selected_index),
    )

    page.add(
        ft.Column(
            [
                ft.Row(
                    [
                        ft.Text("Visual Template Automation Toolkit", size=22, weight=ft.FontWeight.W_700),
                        ft.Row(
                            [
                                status_text,
                                ft.IconButton(ft.icons.BRIGHTNESS_6, tooltip="Toggle theme", on_click=alternar_tema),
                            ],
                            spacing=12,
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
                ft.Row([nav, ft.VerticalDivider(width=1), content], expand=True),
            ],
            expand=True,
        )
    )

    carregar_imagens()
    set_view(0)


def run():
    """Inicia a interface gráfica da aplicação usando Flet."""
    ft.app(target=main)
