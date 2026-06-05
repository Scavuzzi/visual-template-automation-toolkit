import ctypes
import json
import logging
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import cv2
import numpy as np
import pyautogui
import pyperclip

try:
    import win32con
    import win32gui
    import win32com.client
except ImportError:  # pragma: no cover - depende do Windows/pywin32
    win32con = None
    win32gui = None
    win32com = None


logger = logging.getLogger(__name__)
pyautogui.FAILSAFE = True

CONFIG_FILE = Path("config.json")

DEFAULT_CONFIG = {
    "confidence": 0.8, # Padrão de confiança para reconhecimento de imagem (0.0 a 1.0)
    "sleep_extra": 0.0, # Tempo extra (em segundos) adicionado a todas as esperas para compensar variações de desempenho
    "image_scale_min": 0.8, # Escala mínima para redimensionamento de templates (ex: 0.8 = 80% do tamanho original)
    "image_scale_max": 1.6, # Escala máxima para redimensionamento de templates (ex: 1.6 = 160% do tamanho original)
    "image_scale_steps": 17, # Número de passos entre a escala mínima e máxima para tentar encontrar o template
    "images_dir": "assets/images", # Diretório padrão onde os templates de imagem são armazenados
    "backup_dir": "assets/backup", # Diretório onde screenshots de falhas ou imagens de debug podem ser salvas
    "theme_mode": "dark", # Modo de tema para logs e mensagens (ex: "dark" ou "light") - pode ser usado para ajustar cores em logs ou GUIs futuras
}


def load_config(config_path: str | os.PathLike = CONFIG_FILE) -> dict: 
    """
    Carrega a configuração do arquivo JSON, retornando um dicionário com os valores. Se o arquivo não existir ou for inválido, retorna os valores padrão.

    :param config_path: Caminho para o arquivo de configuração JSON (padrão: "config.json").
    :returns: Dicionário contendo as configurações carregadas do arquivo ou os valores padrão.
    """
    config = DEFAULT_CONFIG.copy()
    path = Path(config_path)

    if path.exists():
        try:
            with path.open("r", encoding="utf-8") as file:
                config.update(json.load(file) or {})
        except Exception as exc:
            logger.warning("Falha ao ler config.json; usando defaults: %s", exc)

    return config


def save_config(config: dict, config_path: str | os.PathLike = CONFIG_FILE) -> None:
    """
    Salva a configuração fornecida em um arquivo JSON, mesclando-a com os valores padrão para garantir que todas as chaves estejam presentes.

    :param config: Dicionário contendo as configurações a serem salvas.
    :param config_path: Caminho para o arquivo de configuração JSON onde os dados serão salvos (padrão: "config.json").
    """
    merged = DEFAULT_CONFIG.copy()
    merged.update(config)

    path = Path(config_path)
    with path.open("w", encoding="utf-8") as file:
        json.dump(merged, file, ensure_ascii=False, indent=2)


def sleep_padrao(segundos: float, config: Optional[dict] = None) -> None:
    """
    Realiza uma pausa por um número de segundos, adicionando um tempo extra definido na configuração para compensar variações de desempenho.

    :param segundos: Tempo base de espera em segundos.
    :param config: Dicionário de configuração que pode conter a chave "sleep_extra" para adicionar tempo extra à espera (opcional). Se não fornecido, a configuração será carregada do arquivo padrão.
    """
    cfg = config or load_config()
    time.sleep(segundos + float(cfg.get("sleep_extra", 0.0)))


@dataclass(frozen=True) # Imutável para garantir que os dados do match não sejam alterados após a criação
class ImageMatch:
    """
    Representa o resultado de uma tentativa de encontrar um template de imagem na tela, contendo informações sobre a posição, tamanho, escala e confiança do match.
    """
    template_path: Path
    top_left: tuple[int, int]
    size: tuple[int, int]
    score: float
    scale: float

    @property # property transforma o método em um atributo calculado, permitindo acessar o centro do match como uma propriedade sem precisar chamar um método (ou seja, usar match.center em vez de match.center())
    def center(self) -> tuple[int, int]:
        """
        # Calcula o centro do retângulo do match com base na posição superior esquerda e no tamanho do template encontrado, retornando as coordenadas (x, y) do centro.
        """
        width, height = self.size
        return (
            self.top_left[0] + width // 2,
            self.top_left[1] + height // 2,
        )


class VisualAutomation:
    """Base reutilizavel para automacoes guiadas por reconhecimento de imagem."""

    def __init__(
        self,
        config_path: str | os.PathLike = CONFIG_FILE,
        stop_event=None,
    ) -> None:
        self.config_path = Path(config_path)
        self.config = load_config(self.config_path)
        self.stop_event = stop_event
        self._running = True

    def parar(self) -> None:
        """
        Sinaliza internamente que a automação deve ser interrompida.

        A interrupção é percebida pelas rotinas que chamam `_check_stop()`
        durante esperas, buscas de imagem ou execuções de fluxo.
        """

        logger.warning("[STOP] Sinal de parada recebido.")
        self._running = False

    def reload_config(self) -> dict:
        """
        Recarrega a configuração do arquivo JSON, atualizando os valores usados pela automacao. Retorna o dicionário de configuração atualizado.

        :returns: Dicionário contendo as configurações recarregadas do arquivo JSON.
        """
        self.config = load_config(self.config_path)
        return self.config

    def _check_stop(self) -> None:
        """
        Verifica se a automacao deve ser interrompida, verificando o estado interno e o evento de parada. Se a automacao estiver sinalizada para parar, levanta uma exceção InterruptedError para interromper a execução.
        """
        if not self._running:
            raise InterruptedError("Automacao interrompida pelo usuario.")

        if self.stop_event and self.stop_event.is_set():
            raise InterruptedError("Automacao interrompida pelo usuario.")

    def checar_resolucao(self) -> tuple[int, int]:
        """
        Verifica a resolução atual da tela usando a API do Windows para garantir que a automacao esteja operando na resolução esperada.
        
        :returns: Tupla contendo a largura e altura da tela em pixels (largura, altura).
        """
        user32 = ctypes.windll.user32
        user32.SetProcessDPIAware()
        largura = user32.GetSystemMetrics(0)
        altura = user32.GetSystemMetrics(1)
        logger.info("[INFO] Resolucao atual: %sx%s", largura, altura)
        return largura, altura

    def focar_janela(self, parte_titulo: str) -> bool:
        """
        Foca a janela do aplicativo que contém a parte especificada no título, trazendo-a para o primeiro plano.

        :param parte_titulo: String que deve estar presente no título da janela para ser focada (comparação case-insensitive).
        :returns: True se a janela foi encontrada e focada com sucesso, False caso contrário
        """
        if win32gui is None or win32con is None:
            raise RuntimeError("pywin32 nao esta disponivel para focar janelas.")

        janelas_encontradas = []

        def enum_janelas(hwnd, janelas):
            """
            Função de callback para enumerar janelas, verificando se cada janela é visível e se seu título contém a parte especificada. Se uma janela corresponder, ela é adicionada à lista de janelas encontradas.

            :param hwnd: Handle da janela sendo verificada.
            :param janelas: Lista onde as janelas correspondentes serão armazenadas como tuplas (hwnd, titulo).
            """
            if win32gui.IsWindowVisible(hwnd):
                titulo = win32gui.GetWindowText(hwnd)
                if parte_titulo.lower() in titulo.lower():
                    janelas.append((hwnd, titulo))

        win32gui.EnumWindows(enum_janelas, janelas_encontradas)

        if not janelas_encontradas:
            logger.error("[ERRO] Nenhuma janela contendo '%s' foi encontrada.", parte_titulo)
            return False

        hwnd, titulo = janelas_encontradas[0]
        logger.info("[INFO] Janela encontrada: '%s'", titulo)

        try:
            shell = win32com.client.Dispatch("WScript.Shell")
            shell.SendKeys("%")
            win32gui.ShowWindow(hwnd, win32con.SW_SHOW)
            win32gui.SetForegroundWindow(hwnd)
            logger.info("[OK] Janela '%s' trazida para frente.", titulo)
            return True
        except Exception as exc:
            logger.error("[ERRO] Falha ao focar janela: %s", exc)
            return False

    def screenshot_bgr(self) -> np.ndarray:
        """
        Captura uma screenshot da tela usando pyautogui e converte a imagem para o formato BGR usado pelo OpenCV, retornando a imagem como um array NumPy.

        :returns: Imagem da tela como um array NumPy no formato BGR (altura, largura, canais).
        """
        
        tela = pyautogui.screenshot()
        return cv2.cvtColor(np.array(tela), cv2.COLOR_RGB2BGR)

    def encontrar_imagem(
        self,
        template_path: str | os.PathLike,
        escala_min: Optional[float] = None,
        escala_max: Optional[float] = None,
        passos: Optional[int] = None,
        threshold: Optional[float] = None,
    ) -> Optional[ImageMatch]:
        """
        Busca por um template de imagem na tela, tentando diferentes escalas dentro dos limites especificados.

        :param template_path: Caminho para o arquivo de imagem do template a ser encontrado.
        :param escala_min: Escala mínima para redimensionamento do template (opcional, se não fornecido, será usado o valor da configuração "image_scale_min").
        :param escala_max: Escala máxima para redimensionamento do template (opcional, se não fornecido, será usado o valor da configuração "image_scale_max").
        :param passos: Número de passos entre a escala mínima e máxima para tentar encontrar o template (opcional, se não fornecido, será usado o valor da configuração "image_scale_steps").
        :param threshold: Limite de confiança para considerar um match como válido (opcional, se não fornecido, será usado o valor da configuração  "confidence").
        :returns: Um objeto ImageMatch contendo os detalhes do match encontrado, ou None se nenhum match atender ao critério de confiança.
        """
        self._check_stop()
        self.reload_config()

        template_path = Path(template_path)
        template = cv2.imread(str(template_path))
        if template is None:
            logger.error("[ERRO] Template nao encontrado: %s", template_path)
            return None

        escala_min = float(escala_min or self.config.get("image_scale_min", 0.8))
        escala_max = float(escala_max or self.config.get("image_scale_max", 1.2))
        passos = int(passos or self.config.get("image_scale_steps", 10))
        threshold = float(threshold or self.config.get("confidence", 0.8))

        tela = self.screenshot_bgr()
        template_h, template_w = template.shape[:2]
        best_match = None

        for escala in np.linspace(escala_min, escala_max, passos):
            width = max(1, int(template_w * escala))
            height = max(1, int(template_h * escala))
            template_resized = cv2.resize(template, (width, height))

            if height > tela.shape[0] or width > tela.shape[1]:
                continue

            result = cv2.matchTemplate(tela, template_resized, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, max_loc = cv2.minMaxLoc(result)

            if best_match is None or max_val > best_match.score:
                best_match = ImageMatch(
                    template_path=template_path,
                    top_left=(int(max_loc[0]), int(max_loc[1])),
                    size=(width, height),
                    score=float(max_val),
                    scale=float(escala),
                )

        if best_match and best_match.score >= threshold:
            logger.info(
                "[OK] %s encontrada em %s com confianca %.2f e escala %.2f",
                template_path.name,
                best_match.center,
                best_match.score,
                best_match.scale,
            )
            return best_match

        score = best_match.score if best_match else 0.0
        logger.debug("[DEBUG] %s nao encontrada. Melhor score: %.2f", template_path.name, score)
        return None

    def aguardar_imagem(
        self,
        template_path: str | os.PathLike,
        timeout: float = 15,
        delay: float = 0.5,
        **kwargs,
    ) -> Optional[ImageMatch]:
        """
        Aguarda até que um template de imagem seja encontrado na tela, verificando periodicamente dentro do tempo limite especificado.

        :param template_path: Caminho para o arquivo de imagem do template a ser encontrado.
        :param timeout: Tempo máximo em segundos para aguardar o template antes de desistir (padrão: 15 segundos).
        :param delay: Tempo em segundos entre cada tentativa de verificação da imagem (padrão: 0.5 segundos).
        :param kwargs: Argumentos adicionais a serem passados para o método encontrar_imagem (como escala_min, escala_max, passos, threshold).
        :returns: Um objeto ImageMatch contendo os detalhes do match encontrado, ou None se o template não for encontrado dentro do tempo limite.
        """

        inicio = time.time()

        while time.time() - inicio < timeout:
            self._check_stop()
            match = self.encontrar_imagem(template_path, **kwargs)
            if match:
                return match
            time.sleep(delay)

        return None

    def encontrar_a_imagem(
        self,
        template_path: str | os.PathLike,
        timeout: float = 10,
        delay: float = 0.5,
        **kwargs,
    ) -> Optional[tuple[int, int]]:
        """
        Busca por um template de imagem na tela e retorna as coordenadas do centro do match encontrado. Aguarda até que o template seja encontrado ou o tempo limite seja atingido.

        :param template_path: Caminho para o arquivo de imagem do template a ser encontrado.
        :param timeout: Tempo máximo em segundos para aguardar o template antes de desistir (padrão: 10 segundos).
        :param delay: Tempo em segundos entre cada tentativa de verificação da imagem (padrão: 0.5 segundos).
        :param kwargs: Argumentos adicionais a serem passados para o método encontrar_imagem (como escala_min, escala_max, passos, threshold).
        :returns: Tupla contendo as coordenadas (x, y) do centro do match encontrado, ou None se o template não for encontrado dentro do tempo limite. 
        """

        match = self.aguardar_imagem(template_path, timeout=timeout, delay=delay, **kwargs)
        return match.center if match else None

    def encontrar_e_clicar(
        self,
        template_path: str | os.PathLike,
        offset_x: int = 0,
        offset_y: int = 0,
        timeout: float = 15,
        delay: float = 0.5,
        clicks: int = 1,
        button: str = "left",
        **kwargs,
    ) -> bool:
        """
        Encontra um template de imagem na tela e realiza um clique nas coordenadas do centro do match encontrado, aplicando os offsets especificados. Aguarda até que o template seja encontrado ou o tempo limite seja atingido.

        :param template_path: Caminho para o arquivo de imagem do template a ser encontrado.
        :param offset_x: Deslocamento horizontal em pixels a ser aplicado às coordenadas do clique (padrão: 0).
        :param offset_y: Deslocamento vertical em pixels a ser aplicado às coordenadas do clique (padrão: 0).
        :param timeout: Tempo máximo em segundos para aguardar o template antes de desistir (padrão: 15 segundos).
        :param delay: Tempo em segundos entre cada tentativa de verificação da imagem (padrão: 0.5 segundos).
        :param clicks: Número de cliques a serem realizados (padrão: 1).
        :param button: Botão do mouse a ser clicado ("left", "right" ou "middle", padrão: "left").
        :param kwargs: Argumentos adicionais a serem passados para o método encontrar_imagem (como escala_min, escala_max, passos, threshold).
        :returns: True se o clique foi realizado com sucesso, False se o template não for encontrado dentro do tempo limite ou se ocorrer um erro durante o clique.
        """

        match = self.aguardar_imagem(template_path, timeout=timeout, delay=delay, **kwargs)
        if not match:
            logger.error("[ERRO] Nao foi possivel clicar em %s.", Path(template_path).name)
            return False

        x, y = match.center
        x += offset_x
        y += offset_y

        pyautogui.moveTo(x, y, duration=0.2)
        pyautogui.click(x=x, y=y, clicks=clicks, interval=0.1, button=button)
        logger.info("[OK] Clique realizado em (%s, %s)", x, y)
        time.sleep(delay)
        return True

    def clique_duplo(self, template_path: str | os.PathLike, **kwargs) -> bool:
        """
        Realiza um clique duplo em um template de imagem encontrado na tela, aplicando os mesmos parâmetros de busca e clique do método encontrar_e_clicar.

        :param template_path: Caminho para o arquivo de imagem do template a ser encontrado.
        :param kwargs: Argumentos adicionais a serem passados para o método encontrar_e_clicar (como offset_x, offset_y, timeout, delay, button, escala_min, escala_max, passos, threshold).
        :returns: True se o clique duplo foi realizado com sucesso, False se o template não for encontrado dentro do tempo limite ou se ocorrer um erro durante o clique.
        """
        return self.encontrar_e_clicar(template_path, clicks=2, **kwargs)

    def colar_texto(self, texto: str) -> None:
        """
        Copia o texto fornecido para a área de transferência usando pyperclip e em seguida cola o texto usando o atalho de teclado Ctrl+V.

        :param texto: String contendo o texto a ser colado.
        """
        pyperclip.copy(str(texto))
        pyautogui.hotkey("ctrl", "v")
        logger.info("[INFO] Texto colado com sucesso.")

    def limpar_campo_bruto(self, backspaces: int = 30, delay: float = 0.01) -> None:
        """
        Realiza uma limpeza bruta de um campo de texto, enviando uma sequência de backspaces e deletes para garantir que o campo esteja vazio. O número de backspaces e o delay entre cada tecla podem ser configurados.

        :param backspaces: Número de backspaces a serem enviados para limpar o campo (padrão: 30).
        :param delay: Tempo em segundos entre cada tecla de backspace/delete enviada (padrão: 0.01 segundos).
        """
        for _ in range(backspaces):
            self._check_stop()
            pyautogui.press("backspace")
            pyautogui.press("delete")
            time.sleep(delay)

    def preencher_campo(
        self,
        template_path: str | os.PathLike,
        texto: str,
        timeout: float = 10,
        delay: float = 0.5,
        tecla_final=None,
        offset_x: int = 0,
        offset_y: int = 0,
    ) -> bool:
        """
        Encontra um template de imagem na tela, clica para focar o campo correspondente, limpa o campo usando uma abordagem bruta e cola o texto fornecido. Opcionalmente, pode enviar uma tecla final após colar o texto (como "enter" ou "tab") e aplicar offsets ao clique.

        :param template_path: Caminho para o arquivo de imagem do template a ser encontrado.
        :param texto: String contendo o texto a ser colado no campo encontrado.
        :param timeout: Tempo máximo em segundos para aguardar o template antes de desistir (padrão: 10 segundos).
        :param delay: Tempo em segundos entre cada etapa do processo (padrão: 0.5 segundos).
        :param tecla_final: Tecla ou lista de teclas a serem pressionadas após colar o texto (opcional, ex: "enter", "tab" ou ["ctrl", "s"]).
        :param offset_x: Deslocamento horizontal em pixels a ser aplicado às coordenadas do clique para focar o campo (padrão: 0).
        :param offset_y: Deslocamento vertical em pixels a ser aplicado às coordenadas do clique para focar o campo (padrão: 0).
        :returns: True se o campo foi preenchido com sucesso, False se o template não for encontrado dentro do tempo limite ou se ocorrer um erro durante o processo.
        """
        if not self.encontrar_e_clicar(
            template_path,
            timeout=timeout,
            delay=delay,
            offset_x=offset_x,
            offset_y=offset_y,
        ):
            """
            Se o template não for encontrado e clicado com sucesso, registra um erro e retorna False para indicar que o campo não foi preenchido.
            """
            return False

        sleep_padrao(0.5, self.config)
        self.limpar_campo_bruto()
        sleep_padrao(0.5, self.config)
        self.colar_texto(texto)

        if tecla_final:
            if isinstance(tecla_final, list):
                pyautogui.hotkey(*tecla_final)
            else:
                pyautogui.press(tecla_final)

        logger.info("[OK] Campo preenchido usando template %s.", Path(template_path).name)
        return True

    def listar_templates(self, images_dir: str | os.PathLike | None = None) -> list[Path]:
        """
        Lista os arquivos de template de imagem disponíveis no diretório especificado ou no diretório padrão definido na configuração.

        :param images_dir: Caminho para o diretório onde os templates de imagem estão armazenados (opcional, se não fornecido, será usado o valor da configuração "images_dir").
        :returns: Lista de objetos Path para os arquivos de imagem encontrados no diretório especificado
        """
        pasta = Path(images_dir or self.config.get("images_dir", "assets/images"))
        extensoes = {".png", ".jpg", ".jpeg", ".bmp"}
        return sorted(path for path in pasta.glob("*") if path.suffix.lower() in extensoes)
