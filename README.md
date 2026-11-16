# SonicFetch Desktop (Windows) — Extrator de Áudio de Máxima Fidelidade para UVR5

Aplicativo desktop nativo para **Windows 10/11** em **Python + PySide6 (Qt 6)** focado na extração de faixas de áudio do **YouTube** e **YouTube Music** preservando a fidelidade original para separação de stems por IA no **Ultimate Vocal Remover 5 (UVR5)**.

## Principais Recursos

- **Perfis Calibrados para UVR5 (Sem Recodificação Silenciosa):**
  - **Original Bruto (Bit-Exact):** Baixa o stream nativo (`Opus 251/774` ou `AAC 140/141`) bit a bit sem `-x` nem filtros de áudio, com opção de remux sem perdas `.webm` → `.opus` (`ffmpeg -c:a copy`).
  - **M4A / AAC Nativo Puro:** Prioriza `141` (256 kbps Premium) ou `140` sem re-encoding.
  - **WAV (PCM Sem Perdas de Geração):** Converte diretamente para WAV preservando o sample rate original da fonte (`48 kHz` no Opus ou `44.1 kHz` no AAC), com opção explícita para forçar `44.1 kHz / 16-bit` apenas se necessário.
- **Descoberta de Masters (`- Topic`):** Identifica faixas oficiais do YouTube Music e inclui buscador dedicado *"Buscar versão - Topic (Master)"*.
- **Integração Direta com UVR5:** Arraste itens concluídos diretamente da fila do SonicFetch para a janela do **UVR5** ou Windows Explorer (`QDrag` nativo).
- **Gerenciador Autônomo de Binários:** Detecta, baixa e atualiza `yt-dlp.exe`, `ffmpeg.exe` e `ffprobe.exe` pela interface gráfica sem exigir configuração manual de `PATH`.
- **Auditoria Técnica (`ffprobe`) & Console Técnico:** Mostra comandos executados, logs em tempo real e inspeciona codec/sample rate/bitrate reais do arquivo salvo.

## Execução em Desenvolvimento

Para abrir rapidamente no Windows sem terminal, dê um duplo clique em **`SonicFetch.bat`** (ou execute manualmente):

```powershell
# 1. Criar e ativar ambiente virtual
uv venv .venv --python 3.11
.venv\Scripts\activate

# 2. Instalar dependências
uv pip install -r requirements.txt

# 3. Executar aplicativo (ou duplo clique em SonicFetch.bat)
python -m src.main
```

## Testes Automatizados

```powershell
.venv\Scripts\python.exe -m pytest
```

## Empacotamento Standalone (.exe)

```powershell
.\build_exe.ps1
```

O executável será gerado em `dist\SonicFetchDesktop\SonicFetchDesktop.exe`.
