# PRD — SonicFetch Desktop (Windows) — Extrator de Áudio de Máxima Fidelidade para UVR5

---

## 1. Visão Geral do Produto

### 1.1 Objetivo
Desenvolver um aplicativo desktop nativo para **Windows 10/11** em **Python + PySide6 (Qt 6)**, projetado especificamente para extrair faixas de áudio do **YouTube** e **YouTube Music** com a **máxima fidelidade possível**, pronto para processamento de separação de stems por IA no **Ultimate Vocal Remover 5 (UVR5)**.

### 1.2 Contexto e Motivação
* O projeto anterior (`SonicFetch` em `baixarAudio`) é exclusivo para Android (`Jetpack Compose`, `ForegroundService`, `MediaStore`, `youtubedl-android`) e realiza conversão/reamostragem forçada para `44.1 kHz` orientada a players comuns e MP3.
* No fluxo de trabalho profissional com **UVR5**, a qualidade da separação de vocais, bateria, baixo e instrumentais depende diretamente de preservar o **fluxo de áudio bruto original** entregue pelos servidores do Google, evitando:
  * **Dupla compressão (re-encoding)** — especialmente conversão para **MP3**, que aplica um segundo corte espectral e descarta altas frequências necessárias para os modelos de IA do UVR5.
  * **Reamostragem (resampling) desnecessária** — ex.: forçar `44.1 kHz` sobre fluxos nativos **Opus (48 kHz)** antes da entrada no UVR5.

### 1.3 Proposta de Valor
* **Preservação Bit-Exact:** Baixa o stream nativo original — **Opus/WebM (ID 251)** ou **AAC/M4A (ID 140 / ID 141)** — sem alterar um único bit quando o usuário escolhe o modo bruto.
* **Decodificação Limpa para WAV:** Quando o usuário optar por WAV, converte diretamente a partir do melhor stream nativo **preservando o sample rate original da fonte** (48 kHz ou 44.1 kHz).
* **Integração Direta com UVR5:** Suporte a **Drag & Drop nativo do Windows** para arrastar arquivos concluídos diretamente da janela do app para dentro do UVR5.
* **Descoberta de Masters Oficiais (`- Topic`):** Identifica e busca versões geradas automaticamente pelo YouTube Music (`Artista - Topic`), que utilizam a master de estúdio enviada pelas gravadoras sem compressão extra nem ruídos de videoclipes.
* **Autônomo e Sem Terminal:** Gerencia e atualiza `yt-dlp.exe` e `ffmpeg.exe` automaticamente pela interface gráfica.

---

## 2. Público-Alvo e Casos de Uso

### 2.1 Público-Alvo
* Músicos, produtores musicais, arranjadores e usuários do **UVR5** no Windows que precisam de stems limpos (acapella, instrumental, bateria, baixo, guitarra/piano).
* Usuários que desejam máxima fidelidade sonora sem precisar memorizar comandos de terminal do `yt-dlp`.

### 2.2 Casos de Uso Principais
1. **Download Bit-Exact de Faixa Única para UVR5:** O usuário cola o link -> inspeciona o stream nativo (`251` Opus ou `140/141` M4A) -> baixa em modo Bruto -> arrasta o arquivo da lista do app diretamente para o UVR5.
2. **Troca de Videoclipe para Versão `- Topic`:** O usuário cola o link de um videoclipe oficial com intro falada ou compressão de vídeo -> clica em *"Buscar versão - Topic"* -> escolhe a faixa oficial do YouTube Music -> baixa a master limpa.
3. **Extração em Lote (Playlists / Álbuns):** O usuário cola a URL de uma playlist/álbum -> seleciona todas ou parte das faixas -> baixa na fila para usar o *Batch Mode* do UVR5.
4. **Acesso a Streams Premium (ID 141 / 774):** O usuário ativa cookies do navegador (Edge/Chrome/Firefox) para autenticar sua conta YouTube Music Premium e desbloquear **AAC 256 kbps (ID 141)** ou **Opus 256 kbps (ID 774)** e evitar bloqueios anti-bot.

---

## 3. Requisitos Funcionais (FR)

### FR-01: Entrada de Links e Detecção Inteligente
* Campo de URL principal com botões de **Colar**, **Limpar** e **Analisar**.
* Opção de monitoramento/leitura automática da área de transferência ao focar a janela (configurável).
* Sanitização inteligente de URLs: preserva `v=` e opcionalmente `list=` quando for playlist, removendo parâmetros de rastreamento (`si=`, `pp=`, timestamps `t=`) quando aplicável, e mantendo opção de tratar URL mista (`watch?v=...&list=...`) como **Apenas vídeo** ou **Playlist inteira** (perguntando/indicando claramente na UI).
* Suporte a URLs de `youtube.com`, `youtu.be`, `music.youtube.com` e termos de busca direta.

### FR-02: Inspetor Técnico de Metadados e Streams (`--dump-json`)
* Antes de iniciar o download, o app consulta os metadados completos sem baixar o arquivo:
  * Capa (thumbnail em alta resolução).
  * Título da faixa, Canal/Artista e Duração formatada (`MM:SS` / `HH:MM:SS`).
  * **Indicador de Fonte Master:** Badge visual verde **`Master / - Topic`** quando o canal terminar em ` - Topic` ou a URL for do `music.youtube.com`; caso contrário, badge neutra **`Vídeo Padrão`**.
* **Tabela / Seletor de Streams de Áudio Disponíveis:**
  * Lista todos os streams *audio-only* retornados pelo YouTube com:
    * **Format ID** (ex.: `251`, `140`, `141`, `774`, `250`, `249`).
    * **Codec** (`opus`, `mp4a.40.2`).
    * **Contêiner / Extensão** (`webm`, `m4a`).
    * **Bitrate médio (`abr`)** em kbps (ex.: `~138 kbps`, `129 kbps`, `256 kbps`).
    * **Taxa de Amostragem (`asr`)** em Hz (ex.: `48000 Hz`, `44100 Hz`).
    * **Tamanho estimado** em MB.
  * Seleção automática inteligente pelo perfil ativo, permitindo ao usuário avançado fixar manualmente um `Format ID` específico.

### FR-03: Perfis de Extração Calibrados para UVR5
O aplicativo deve oferecer perfis claros e auditáveis, **sem recodificação silenciosa**:

1. **Original Bruto — UVR5 Recomendado (Bit-Exact)** *(Padrão)*:
   * Seletor: `bestaudio[acodec=opus]/bestaudio[ext=m4a]/bestaudio` (ou `format_id` selecionado pelo usuário).
   * **Regra crítica:** Não passa `-x` nem filtros de áudio (`-ar`, `-ac`, `-b:a`). O arquivo `.webm` (Opus 251) ou `.m4a` (AAC 140/141) é salvo **bit a bit** exatamente como recebido do servidor.
   * Opção secundária *"Extrair contêiner sem recodificar"*: executa apenas remuxing sem perda (`ffmpeg -c:a copy`, ex.: `.webm` → `.opus`), se o usuário preferir extensão `.opus`.
2. **M4A / AAC Nativo Puro**:
   * Prioriza `bestaudio[ext=m4a]/bestaudio[acodec^=mp4a]` (ID `141` quando disponível via cookies Premium; senão ID `140`).
   * Sem re-encoding.
3. **WAV (PCM Sem Perdas de Geração)**:
   * Executa `yt-dlp -f bestaudio -x --audio-format wav` diretamente sobre o melhor fluxo nativo.
   * **Regra crítica:** **Não** injeta `-ar 44100` por padrão, preservando a taxa de amostragem original da fonte (48 kHz no Opus ou 44.1 kHz no AAC).
   * Sub-opção avançada (desmarcada por padrão): *"Forçar 44.1 kHz / 16-bit (CD / Teclados / DAWs legadas)"*.
4. **Bloqueio / Isolamento de MP3:**
   * MP3 **não** faz parte dos perfis UVR5.
   * Caso um perfil legado MP3 seja habilitado nas Configurações Avançadas, deve exibir um aviso explícito na UI: *"Atenção: MP3 aplica dupla compressão com perda e reduz a qualidade da separação no UVR5"*.

### FR-04: Buscador Integrado de Versão `- Topic` (YouTube Music)
* Botão **"Buscar versão - Topic (Master)"** ao lado do preview quando o vídeo atual não for `- Topic`.
* Executa busca rápida (`yt-dlp --dump-json --flat-playlist "ytsearch5:<título_limpo> topic"`) e apresenta até 5 resultados com título, canal, duração e indicação de quais terminam em `- Topic`.
* Ao selecionar um resultado, substitui o preview atual pelo link oficial `- Topic` pronto para inspeção/download.

### FR-05: Suporte a Cookies e Contorno de Restrições
* Configuração de autenticação opcional na barra superior ou tela de Configurações:
  * **Desativado** (padrão).
  * **Importar do Navegador (`--cookies-from-browser`)**: Edge, Chrome, Firefox, Brave, Opera.
  * **Arquivo manual (`--cookies <caminho/cookies.txt>`)**.
* Exibe na UI quando um stream de alta taxa de bits autenticado (ex.: ID `141` 256 kbps AAC ou ID `774` 256 kbps Opus) for detectado.

### FR-06: Fila de Downloads, Playlists e Controle de Concorrência
* Fila visual com múltiplos itens e estados claros:
  * `Na fila` → `Analisando streams` → `Baixando fluxo bruto` → `Convertendo p/ WAV (FFmpeg)` → `Finalizando` → `Concluído` / `Cancelado` / `Erro`.
* Progresso em tempo real por item:
  * Barra percentual (`0%–100%`).
  * Velocidade de download (`MB/s` / `KiB/s`).
  * ETA restante e tamanho baixado/total.
  * `Format ID` e codec efetivamente sendo baixados.
* Limite configurável de downloads simultâneos (padrão: `2`, configurável de `1` a `4`) para não saturar rede/CPU.
* Suporte a playlists: modal/painel de seleção de faixas antes de enfileirar todas no lote.
* Ações na fila: Pausar/Cancelar item, Cancelar todos, Remover concluídos, Tentar novamente em caso de erro.

### FR-07: Integração Direta com UVR5 e Sistema de Arquivos
* **Drag & Drop Nativo (Qt `QDrag` + `QMimeData` com `QUrl.fromLocalFile`):**
  * Qualquer item com status `Concluído` na lista pode ser clicado e arrastado diretamente da janela do SonicFetch Desktop para a janela do **Ultimate Vocal Remover 5** (ou para o Windows Explorer / DAW).
* Ações rápidas por arquivo concluído:
  * **Abrir no Explorer** (abre o Windows Explorer já com o arquivo selecionado via `explorer /select,"<caminho>"`).
  * **Copiar Caminho** (útil para colar no seletor de arquivo do UVR5).
  * **Pré-escuta Rápida** (botão play/pause leve opcional usando `QMediaPlayer` / `QAudioOutput`).
  * **Excluir Arquivo**.

### FR-08: Nomeação, Organização e Sidecar de Auditoria
* Pasta de saída configurável (padrão: `%USERPROFILE%\Music\SonicFetch_UVR5` ou pasta escolhida pelo usuário).
* Template de nome configurável com presets:
  * `%(uploader)s - %(title)s [%(format_id)s].%(ext)s` (padrão recomendado para saber qual ID foi baixado).
  * `%(title)s.%(ext)s`.
  * `%(playlist_index)02d - %(title)s.%(ext)s` (para playlists).
* Sanitização segura para Windows (`--windows-filenames` + limpeza de caracteres reservados e proteção contra paths > 260 caracteres).
* Política configurável de arquivo existente: *Pular*, *Sobrescrever*, *Renomear automaticamente*.
* **Metadados sem perda:** `--add-metadata` apenas quando suportado sem recodificação (`.m4a`, `.webm`/`.opus` via remux), evitando modificar o bitstream de áudio. Opção de gerar arquivo `.json` sidecar (`--write-info-json` enxuto) para auditoria técnica se o usuário quiser conferir bitrate/codec depois.

### FR-09: Gerenciador Autônomo de Binários (`yt-dlp.exe` e `ffmpeg.exe`)
* O aplicativo não deve exigir que o usuário configure variáveis `PATH` manualmente no Windows.
* Ao iniciar, verifica a disponibilidade dos binários em:
  1. Pasta local do app (`./bin/yt-dlp.exe`, `./bin/ffmpeg.exe`, `./bin/ffprobe.exe`) ou `%LOCALAPPDATA%\SonicFetchWindows\bin\`.
  2. `PATH` do sistema (fallback).
* Se ausentes, exibe assistente/banner claro com botão **"Baixar Dependências Automaticamente"**:
  * Baixa `yt-dlp.exe` diretamente da release oficial (`yt-dlp/yt-dlp` GitHub Releases) com verificação de integridade/tamanho.
  * Baixa build oficial Windows x64 de `ffmpeg.exe` + `ffprobe.exe` (ex.: `BtbN/FFmpeg-Builds` ou `gyan.dev` essentials) e extrai apenas os executáveis necessários para `bin/`.
* Botão dedicado nas Configurações: **"Atualizar yt-dlp agora"** (executa `yt-dlp.exe -U` e exibe versão atual vs. nova versão).

### FR-10: Console Técnico de Transparência e Diagnóstico
* Painel colapsável na parte inferior da janela mostrando:
  * O comando exato executado (`yt-dlp.exe ...`) com máscara em eventuais caminhos sensíveis.
  * Saída em tempo real (`stdout` e `stderr`) do `yt-dlp` e do `ffmpeg`.
  * Botão *"Copiar Log"* e *"Verificar arquivo com ffprobe"* para comprovar codec, bitrate, canais e sample rate finais do arquivo salvo.

---

## 4. Requisitos Não-Funcionais (NFR)

* **NFR-01 (Design & Usabilidade — PySide6 / Qt 6):**
  * Interface moderna em **Dark Mode** inspirada em ferramentas de áudio/estúdio (contraste confortável ao lado do UVR5), com tipografia limpa, espaçamento consistente e janela redimensionável (mínimo `960x640`).
  * Feedback visual imediato em todas as operações assíncronas (spinners/skeletons ao analisar URL).
* **NFR-02 (Arquitetura e Responsividade):**
  * Separação estrita entre **Camada de Domínio/Serviços** (pura em Python, testável sem Qt GUI) e **Camada de Apresentação** (PySide6 Widgets + Signals/Slots).
  * Toda execução de `yt-dlp.exe`, `ffmpeg.exe` e `ffprobe.exe` ocorre fora da thread de UI (`QProcess` ou `QThreadPool` + `subprocess` com encoding UTF-8 e `CREATE_NO_WINDOW` para nunca abrir janelas pretas de CMD piscando na tela).
  * Cancelamento deve encerrar imediatamente o processo filho e quaisquer subprocessos (`ffmpeg`) no Windows, removendo arquivos `.part` / `.ytdl` órfãos.
* **NFR-03 (Persistência e Configuração):**
  * Preferências e histórico recente persistidos em `%APPDATA%\SonicFetchWindows\config.json` e `history.json` (ou SQLite leve).
* **NFR-04 (Compatibilidade e Distribuição Windows):**
  * Compatível com **Windows 10 e Windows 11 (x64)**.
  * Executável em modo desenvolvimento (`venv` + `python -m src.main`) e empacotável via **PyInstaller** para distribuição sem exigir Python instalado.
* **NFR-05 (Qualidade de Código e Testes):**
  * Tipagem estática (`type hints` completos + `dataclasses` / `pydantic` opcional).
  * Cobertura de testes unitários com `pytest` para o construtor de comandos `yt-dlp` (garantindo que o modo *Bruto* **nunca** emita flags de re-encoding ou `-ar 44100`), parser de progresso, parser de JSON de streams e sanitização de nomes.

---

## 5. Stack Tecnológica

| Camada / Componente | Tecnologia Escolhida | Justificativa |
| :--- | :--- | :--- |
| **Linguagem** | Python 3.11+ (x64) | Já disponível no ambiente (`3.11.9`), ecossistema maduro e rápido para desenvolvimento. |
| **Interface Gráfica (GUI)** | **PySide6 (Qt 6)** | Suporte nativo a Dark UI moderna, `QDrag` (Drag & Drop real para o UVR5), `QProcess`, tabelas ricas e `QMediaPlayer`. |
| **Motor de Download** | **`yt-dlp.exe`** (binário oficial) | Atualização instantânea via `-U`, suporte completo a formatos `251`/`140`/`141`/`774`, playlists e `--cookies-from-browser`. |
| **Processamento / Inspeção** | **`ffmpeg.exe` + `ffprobe.exe`** | Remuxing sem perdas (`-c:a copy`), decodificação limpa para WAV e auditoria técnica real dos arquivos gerados. |
| **Cliente HTTP (Updater / Thumbs)** | `httpx` (ou `urllib` + `QNetworkAccessManager`) | Download assíncrono de thumbnails e releases de binários com progresso. |
| **Testes Automatizados** | `pytest` + `pytest-qt` | Validação automatizada dos comandos gerados, parsers e interações críticas de UI. |
| **Empacotamento Windows** | `PyInstaller` | Geração de executável Windows standalone para uso diário sem depender de terminal. |

---

## 6. Arquitetura Proposta do Projeto

```text
baixarAudioWindows/
├── PRD.md                          # Este documento de requisitos
├── README.md                       # Guia de instalação, uso e build
├── pyproject.toml                  # Metadados do projeto, dependências e config pytest
├── requirements.txt                # PySide6, httpx, pytest, pytest-qt, pyinstaller
├── bin/                            # Binários gerenciados localmente (yt-dlp.exe, ffmpeg.exe, ffprobe.exe)
├── src/
│   ├── __init__.py
│   ├── main.py                     # Ponto de entrada da aplicação PySide6
│   ├── app_paths.py                # Resolução de pastas (%APPDATA%, bin/, logs/, Downloads)
│   ├── models/
│   │   ├── audio_profile.py        # Enum/Dataclasses dos perfis UVR5 (RAW_OPUS_OR_BEST, RAW_M4A, WAV_NATIVE, etc.)
│   │   ├── stream_info.py          # Modelo de cada stream (format_id, acodec, ext, abr, asr, filesize)
│   │   ├── video_metadata.py       # Metadados do vídeo/playlist + flag is_topic_master
│   │   ├── download_task.py        # Estado do item na fila (status, progress, speed, eta, output_path)
│   │   └── app_settings.py         # Configurações persistentes do usuário
│   ├── core/
│   │   ├── ytdlp_builder.py        # Montagem pura e testável dos argumentos CLI do yt-dlp
│   │   ├── progress_parser.py      # Regex/Parser das linhas de progresso do yt-dlp e FFmpeg
│   │   ├── stream_selector.py      # Lógica de ranqueamento (251/774/141/140) e detecção "- Topic"
│   │   └── filename_utils.py       # Sanitização de nomes e validação de paths no Windows
│   ├── services/
│   │   ├── binary_manager.py       # Verifica, baixa e atualiza yt-dlp.exe e ffmpeg.exe
│   │   ├── inspector_service.py    # Executa --dump-json e ffprobe para inspecionar streams/arquivos
│   │   ├── download_manager.py     # Fila assíncrona com controle de concorrência e cancelamento
│   │   ├── topic_search_service.py # Busca alternativas "- Topic" no YouTube/YouTube Music
│   │   └── settings_store.py       # Leitura/escrita de config.json e history.json
│   └── ui/
│       ├── theme.py                # Paleta Dark Studio (QSS) e estilos globais
│       ├── main_window.py          # Janela principal com abas/painéis e status dos binários
│       ├── widgets/
│       │   ├── url_input_bar.py    # Barra de URL + botões Analisar / Colar / Buscar Topic
│       │   ├── preview_panel.py    # Capa, título, canal, badge "- Topic" e tabela de streams
│       │   ├── profile_selector.py # Seletor dos perfis UVR5 + alertas contra perda de qualidade
│       │   ├── download_queue.py   # Lista da fila + Drag & Drop nativo para UVR5 + ações de arquivo
│       │   ├── playlist_dialog.py  # Modal para seleção de faixas em playlists
│       │   ├── settings_dialog.py  # Pasta padrão, cookies do navegador, templates, updater yt-dlp
│       │   └── log_console.py      # Console técnico colapsável com comandos e saída em tempo real
└── tests/
    ├── test_ytdlp_builder.py       # Garante que perfil Bruto nunca injeta re-encoding ou -ar 44100
    ├── test_progress_parser.py     # Testa parsing de progresso %, velocidade e ETA
    ├── test_stream_selector.py     # Testa seleção entre 251, 141, 140 e detecção "- Topic"
    └── test_filename_utils.py      # Testa sanitização de caracteres inválidos no Windows
```

---

## 7. Fases de Implementação

### Fase 1 — Fundação do Ambiente e Gerenciador de Binários
* Criar ambiente virtual Python (`python -m venv .venv`) e instalar `PySide6`, `httpx`, `pytest`.
* Implementar `app_paths.py`, `settings_store.py` e `binary_manager.py` (detecção e download automático de `yt-dlp.exe`, `ffmpeg.exe` e `ffprobe.exe` sem abrir janelas de console).
* Validar funcionamento dos binários em Windows 10/11.

### Fase 2 — Motor Core de Extração e Auditoria UVR5
* Implementar `ytdlp_builder.py`, `stream_selector.py`, `progress_parser.py` e `inspector_service.py`.
* Garantir que o perfil **Original Bruto** baixe exatamente o `format_id` selecionado (`251`, `140`, `141`, `774`) sem recodificação, e que o perfil **WAV** preserve o sample rate nativo da fonte por padrão.
* Implementar `download_manager.py` com fila concorrente, `CREATE_NO_WINDOW` e cancelamento limpo da árvore de processos.
* Escrever suíte de testes unitários em `tests/` cobrindo todos os perfis e parsers.

### Fase 3 — Interface Desktop PySide6 (MVP Funcional)
* Construir `main_window.py` com tema escuro moderno (`theme.py`).
* Implementar barra de URL, painel de preview com badge `- Topic` e tabela de streams disponíveis (`ID`, `Codec`, `Bitrate`, `Sample Rate`, `Tamanho`).
* Implementar seletor de perfis UVR5, fila de downloads com progresso em tempo real e console técnico colapsável.

### Fase 4 — Produtividade UVR5, Playlists e Empacotamento
* Implementar **Drag & Drop nativo** da lista de concluídos diretamente para o **UVR5** / Windows Explorer.
* Implementar `topic_search_service.py` (botão *"Buscar Master - Topic"*), `playlist_dialog.py` e suporte a `--cookies-from-browser`.
* Adicionar verificação rápida com `ffprobe` no menu de contexto do item concluído.
* Configurar script de build com `PyInstaller` para gerar o executável Windows (`.exe`).

---

## 8. Critérios de Aceite (Definition of Done)

1. **Zero Perda de Geração no Modo Bruto:** Ao baixar um vídeo no perfil *Original Bruto*, o log técnico deve confirmar ausência de transcodificação do FFmpeg e o `ffprobe` do arquivo salvo deve reportar exatamente o mesmo codec (`opus` ou `aac`), bitrate e sample rate (`48000 Hz` ou `44100 Hz`) do stream selecionado.
2. **WAV Fiel à Fonte:** Ao baixar no perfil *WAV UVR5*, o arquivo resultante deve ser `pcm_s16le` (ou configurado) preservando o sample rate nativo original da faixa baixada (sem resampling forçado para 44.1 kHz, salvo se explicitamente ativado pelo usuário).
3. **Fluxo Sem Terminal:** Um usuário sem `yt-dlp` ou `ffmpeg` previamente instalados no Windows consegue abrir o app, baixar as dependências pela própria UI e baixar um áudio completo sem abrir CMD/PowerShell.
4. **Integração UVR5:** Arrastar um arquivo concluído da lista do app diretamente para a janela do **Ultimate Vocal Remover 5** (ou Explorer) carrega o arquivo imediatamente.
5. **Testes Verdes:** Toda a suíte `pytest` dos módulos core (`ytdlp_builder`, `progress_parser`, `stream_selector`, `filename_utils`) passa sem falhas.
