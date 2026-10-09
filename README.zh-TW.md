# MarkItDown Web

<p align="center">
  <a href="README.md">English</a> · <a href="README.zh-TW.md">繁體中文</a>
</p>

<p align="center">
  <a href="#使用方式">使用方式</a> · <a href="#架構">架構</a> · <a href="#開發">開發</a> · <a href="#安全邊界">安全</a>
</p>

<p align="center">
  <img alt="version 1.0.0" src="https://img.shields.io/badge/version-1.0.0-orange">
  <img alt="Python 3.10+" src="https://img.shields.io/badge/python-3.10%2B-blue?logo=python&logoColor=white">
  <img alt="Conda md_webui" src="https://img.shields.io/badge/conda-md__webui-44A833?logo=anaconda&logoColor=white">
  <a href="LICENSE"><img alt="license MIT" src="https://img.shields.io/badge/license-MIT-green"></a>
</p>

一個以 Microsoft MarkItDown 為核心的輕量本機 Web 介面。使用者可以上傳文件，並排查看 Markdown 原始碼與渲染效果；原始碼可直接編輯、複製及下載。介面預設為 en-US，也可以使用語言按鈕切換至 zh-TW。

## 使用方式

在 repository 根目錄執行啟動程式：

- Windows：雙擊 `start.bat`，或在 PowerShell 執行 `.\start.bat`。
- macOS 與 Linux：執行 `./start.sh`。

然後在瀏覽器開啟 `http://localhost:8765`。要停止服務，請在執行中的終端按 `Ctrl+C`。

啟動程式會依下列順序使用找到的 Python 環境：

1. 已安裝 [uv](https://docs.astral.sh/uv/getting-started/installation/) 時：`uv run --no-dev python run.py`（uv 會自動建立並同步 `.venv`）。
2. 既有的 `.venv`；缺少依賴時會安裝 `requirements.txt`。
3. 名為 **`md_webui`** 的 Conda 環境（以 `conda env create -f environment.yml` 建立）。
4. 以上皆無時，使用 `PATH` 上的 Python 3.10 以上版本建立 `.venv` 並安裝 `requirements.txt`。

本專案遵循 MarkItDown 0.1.7 宣告的 Python 版本需求。服務只監聽本機 loopback 介面，不對區域網路或網際網路開放。

## 功能

- 拖放或選取單一文件。
- 使用記憶體串流轉換，不把上傳原始檔寫入磁碟。
- Markdown 程式碼與渲染預覽並排顯示。
- 編輯時即時更新預覽。
- 複製或下載編輯後的 `.md`。
- 64 MB 預設上限，可透過 `MARKITDOWN_WEB_MAX_MB` 調整至 1–512 MB。
- 預覽 HTML 經清理，且停用 Markdown 內嵌 HTML。

支援格式由安裝的 MarkItDown 元件決定。本專案採用常見本機文件格式所需的 extras：PDF、DOCX、PPTX、XLSX、XLS、Outlook MSG，以及核心支援的 HTML、CSV、JSON、XML、文字、EPUB、ZIP、圖片與部分音訊中繼資料。雲端分析、LLM 圖像描述與音訊轉錄未啟用，以降低安裝體積與外部服務依賴。

## 架構

```text
瀏覽器
  ├─ POST /api/convert  ──> FastAPI ──> MarkItDown.convert_stream()
  ├─ POST /api/render   ──> markdown-it-py ──> Bleach 清理
  └─ Blob 下載          ──> 使用者編輯後的 Markdown
```

主要檔案：`app/main.py`（HTTP 端點、大小限制與安全標頭）、`app/converter.py`（MarkItDown 串流轉換封裝）、`app/preview.py`（Markdown 渲染與 HTML 清理）、`app/static/`（無框架前端）、`run.py`（本機服務入口）與 `start.bat` / `start.sh`（啟動程式）。

## 開發

使用 uv：

```bash
uv sync
uv run pytest
uv run ruff check .
uv run python run.py
```

使用 `venv`：

```bash
python -m venv .venv
. .venv/bin/activate
pip install -r requirements-dev.txt
pytest
python run.py
```

使用 Conda：

```bash
conda env create -f environment-dev.yml
conda activate md_webui-dev
pytest
ruff check .
python run.py
```

`environment-dev.yml` 預設會建立名為 **`md_webui-dev`** 的開發 Conda 環境，並安裝 `requirements-dev.txt`；其中包含執行階段依賴、測試與 lint 工具。這些 requirements 檔案是由 uv lockfile 匯出的版本，因此 venv 與 Conda 流程會和 uv 專案保持一致。

依賴套件變更時，請先更新 `pyproject.toml`，執行 `uv lock`，再使用 `uv export` 重新產生兩個 requirements 檔案。

開發指令只提供給維護者；一般使用者不需執行。

## 安全邊界

這是本機桌面用途工具，不是多租戶公開上傳服務。雖然已限制副檔名、檔名與大小，且只使用 `convert_stream()`，仍應只轉換可信文件。若改成對外服務，必須增加程序隔離、資源配額、ZIP 解壓限制、惡意檔案掃描與逾時終止。

## 上游與授權

本專案不包含 Microsoft MarkItDown 的原始碼；`pyproject.toml` 宣告官方 PyPI 套件 `markitdown==0.1.7`，`uv.lock` 記錄解析後的依賴版本，提供的 venv 與 Conda 流程則使用匯出的 requirements 檔案。本介面採 MIT License；第三方套件各自依原授權使用。詳見 `THIRD_PARTY_NOTICES.md`。
