# Visual Template Automation Toolkit

[Prefere ler em ingles? Clique aqui.](README.md)

Um motor de reconhecimento visual para automacao desktop, baseado na identificacao de imagens na tela.

Python | OpenCV | PyAutoGUI | Flet | Automacao Desktop | Visao Computacional

O projeto oferece um motor reutilizavel de reconhecimento por imagem, uma interface em Flet para gerenciar templates visuais e um executor de fluxos baseado em CSV/JSON. Ele foi pensado para ser generico: a aplicacao alvo, os templates e os fluxos sao fornecidos pelo usuario.

Este repositorio e uma versao publica de portfolio/demo. Ele nao inclui templates proprietarios, fluxos de producao, nomes de sistemas internos, credenciais ou dados reais de negocio.

## O Que Ele Faz

- Localiza templates visuais na tela usando OpenCV.
- Testa multiplas escalas de template para tolerar diferencas de tamanho de UI e escala de exibicao.
- Clica, da duplo clique, aguarda e preenche campos com base em templates encontrados.
- Gerencia imagens de template por uma interface leve em Flet.
- Captura novos templates a partir da tela.
- Executa fluxos declarativos em JSON usando linhas de CSV.
- Salva screenshots de falha para ajudar no debug de automacoes quebradas.

## Notas De Plataforma

Este projeto foi pensado principalmente para automacao desktop no Windows.

Ele usa PyAutoGUI para controlar mouse e teclado. Ao rodar testes pela UI ou pelo executor de fluxo, mantenha a janela alvo visivel e evite usar o computador ate a automacao terminar.

O failsafe do PyAutoGUI esta ativado em `core.py`: mova o mouse para um canto da tela para interromper a automacao em uma emergencia.

## Inicio Rapido

```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

## Demo Incluida

Este repositorio inclui um pequeno formulario CRM ficticio e templates prontos, para que o projeto nao fique vazio depois do clone.

- `examples/demo_target.html`: formulario CRM ficticio aberto no navegador.
- `assets/images/demo_*.png`: templates que correspondem a pagina de demo.
- `examples/demo_items.csv`: linhas ficticias usadas pela demo de lote.
- `examples/demo_customers.csv`: clientes ficticios usados pela demo de automacao do formulario.
- `flows/demo_customer_form.json`: fluxo visual declarativo que preenche o formulario.

Para testar o fluxo visual manualmente:

1. Rode `python main.py`.
2. Na UI, va para `Flows`.
3. Clique em `Open demo target`.
4. Mantenha o navegador visivel com zoom em 100%.
5. Clique em `Run flow`.

O app deve preencher o formulario de demo usando linhas de `examples/demo_customers.csv`.

Voce tambem pode ir para `Templates` e clicar no icone de teste ao lado de cada template. O mouse deve se mover ate o elemento visual correspondente na pagina de demo quando o template for detectado.

Para um teste mais confiavel, mantenha o navegador com zoom em 100%. A faixa de escala padrao tambem tolera valores comuns de escala do Windows, como 125% e 150%.

## Screenshots

Formulario vazio:

![Formulario vazio](examples/prints/demo-form-empty.png)

Preenchido pelo fluxo visual:

![Formulario preenchido](examples/prints/demo-form-filled.png)

Estado salvo apos a deteccao do template final:

![Formulario salvo](examples/prints/demo-form-saved.png)

## Rodar A Demo Pelo Terminal

```powershell
python flow_runner.py --open-target --limit 5
```

O comando abre a pagina HTML de demo, le `examples/demo_customers.csv` e executa o fluxo visual de `flows/demo_customer_form.json` para as cinco primeiras linhas.

Para processar todas as linhas da demo:

```powershell
python flow_runner.py --open-target --limit 50
```

## Exemplo De Fluxo

O arquivo de fluxo e propositalmente simples:

```json
{
  "action": "fill_template",
  "template": "demo_label_name.png",
  "value": "{{name}}",
  "offset_x": 250
}
```

Isso significa: encontre o template `demo_label_name.png`, clique 250 pixels a direita dele, limpe o campo alvo e cole o valor de `name` da linha atual do CSV.

Se um template nao for encontrado ou clicado, o executor salva uma screenshot em `logs/screenshots/` para ajudar no debug da falha.

## Acoes De Fluxo

Fluxos JSON atualmente suportam estas acoes:

| Acao | Finalidade |
|---|---|
| `click_template` | Encontra um template e clica no centro dele, com offsets opcionais. |
| `wait_template` | Aguarda ate que um template apareca na tela. |
| `fill_template` | Encontra um template, clica perto dele, limpa o campo alvo e cola um valor. |
| `hotkey` | Envia um atalho de teclado pelo PyAutoGUI. |
| `sleep` | Aguarda uma quantidade fixa de segundos. |

## Estrutura Do Projeto

```text
core.py          Nucleo de automacao visual
interface.py     UI de gerenciamento de templates e tela de execucao de fluxos
reader.py        Demo de leitor de planilhas e separador de lotes
workflows.py     Dispatcher de workflow da demo
flow_runner.py   Executor de fluxo visual em JSON
main.py          Ponto de entrada da UI
examples/        Arquivos de entrada da demo
flows/           Definicoes de fluxo em JSON
assets/images/   Imagens de template usadas em runtime
assets/backup/   Pasta de backup de templates
```

## Rodar A UI

```powershell
python main.py
```

## Rodar A Demo De Planilha

```powershell
python reader.py
```

## Verificacao Manual Sugerida

Antes de usar um novo fluxo visual:

1. Abra a aplicacao alvo.
2. Mantenha a tela relevante visivel.
3. Teste cada template pela aba `Templates`.
4. Rode o fluxo com um `Limit` pequeno, como `1` ou `2`.
5. Verifique `logs/screenshots/` se algum passo falhar.

## Notas De Portfolio

Este projeto foi adaptado como uma demo publica e generica. Templates reais de producao, fluxos privados, nomes de aplicacoes internas e dados de negocio devem ficar fora do repositorio.

Boas ideias de extensao:

- Adicionar validacao tipada para fluxos JSON.
- Adicionar testes unitarios para resolucao de caminhos e interpolacao de valores CSV.
- Dividir a UI em Flet em modulos menores.
- Adicionar um GIF curto mostrando o fluxo de demo rodando.

## Licenca

MIT
