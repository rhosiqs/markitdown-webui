"use strict";

const fileInput = document.getElementById("fileInput");
const chooseButton = document.getElementById("chooseButton");
const dropZone = document.getElementById("dropZone");
const markdownEditor = document.getElementById("markdownEditor");
const markdownPreview = document.getElementById("markdownPreview");
const previewState = document.getElementById("previewState");
const charCounter = document.getElementById("charCounter");
const fileName = document.getElementById("fileName");
const fileMeta = document.getElementById("fileMeta");
const fileType = document.getElementById("fileType");
const copyButton = document.getElementById("copyButton");
const resetButton = document.getElementById("resetButton");
const downloadButton = document.getElementById("downloadButton");

let outputFilename = "converted.md";
let renderTimer = null;
let renderSequence = 0;
let locale = "en-US";

const translations = {
  "en-US": {
    brandTagline: "Local document-to-Markdown workspace", localOnly: "Local only", chooseFile: "Choose file",
    dropTitle: "Drop a document here", dropHint: (max) => `Or click to choose a file, up to ${max} MB`,
    formatHint: "Common formats include PDF, Word, PowerPoint, Excel, HTML, CSV, JSON, XML, EPUB, images, audio, and ZIP.",
    copy: "Copy", clear: "Clear", download: "Download .md", markdownSource: "Markdown source", livePreview: "Live preview",
    emptyPreview: "The rendered result will appear here after conversion.", poweredBy: "Powered by Microsoft MarkItDown", noUpload: "Files are not uploaded to external services",
    editorPlaceholder: "Upload a document and the converted result will appear here.", editorLabel: "Markdown source editor",
    notSelected: "No file selected", afterConvert: "The converted content can be edited below", chars: "characters", waiting: "Waiting for content", updating: "Updating…", synced: "Synced", failed: "Conversion failed", previewError: "Preview error", emptyMarkdown: "Markdown content is empty.",
    ready: (bytes) => `${bytes} · Ready to convert`, output: (bytes, ms, chars) => `${bytes} · ${ms.toLocaleString()} ms · ${chars.toLocaleString()} characters`, conversionFailed: "Conversion failed.", unable: "Unable to complete the conversion.", previewFailed: "Preview failed.", copied: "Copied", switchLanguage: "Chinese"
  },
  "zh-TW": {
    brandTagline: "本機文件轉 Markdown 工作台", localOnly: "僅限本機", chooseFile: "選擇檔案",
    dropTitle: "拖放文件到這裡", dropHint: (max) => `或點擊選擇檔案，單檔上限 ${max} MB`,
    formatHint: "PDF、Word、PowerPoint、Excel、HTML、CSV、JSON、XML、EPUB、圖片、音訊與 ZIP 等常見格式",
    copy: "複製", clear: "清除", download: "下載 .md", markdownSource: "Markdown 程式碼", livePreview: "即時預覽",
    emptyPreview: "轉換後的排版效果會顯示在此處。", poweredBy: "由 Microsoft MarkItDown 驅動", noUpload: "檔案不會上傳至外部服務",
    editorPlaceholder: "上傳文件後，轉換結果會顯示在這裡。", editorLabel: "Markdown 程式碼編輯器",
    notSelected: "尚未選擇檔案", afterConvert: "轉換後可在下方直接編輯", chars: "字元", waiting: "等待內容", updating: "更新中…", synced: "已同步", failed: "轉換失敗", previewError: "預覽錯誤", emptyMarkdown: "Markdown 內容為空。",
    ready: (bytes) => `${bytes} · 準備轉換`, output: (bytes, ms, chars) => `${bytes} · ${ms.toLocaleString()} ms · 輸出 ${chars.toLocaleString()} 字元`, conversionFailed: "轉換失敗。", unable: "無法完成轉換。", previewFailed: "預覽失敗。", copied: "已複製", switchLanguage: "English"
  }
};
const t = (key, ...args) => typeof translations[locale][key] === "function" ? translations[locale][key](...args) : translations[locale][key];
function applyLocale() {
  document.documentElement.lang = locale;
  document.querySelectorAll("[data-i18n]").forEach((element) => {
    const key = element.dataset.i18n;
    element.textContent = key === "dropHint" ? t(key, element.dataset.i18nMax) : t(key);
  });
  document.getElementById("languageSwitch").textContent = t("switchLanguage");
  document.getElementById("dropZone").setAttribute("aria-label", locale === "en-US" ? "Choose or drop a file" : "選擇或拖放檔案");
  markdownEditor.placeholder = t("editorPlaceholder");
  markdownEditor.setAttribute("aria-label", t("editorLabel"));
  updateCounter();
}
document.getElementById("languageSwitch").addEventListener("click", () => {
  locale = locale === "en-US" ? "zh-TW" : "en-US";
  try { localStorage.setItem("markitdown-web-language", locale); } catch {}
  applyLocale();
  resetWorkspace();
});
try {
  const savedLocale = localStorage.getItem("markitdown-web-language");
  if (savedLocale in translations) locale = savedLocale;
} catch {}
applyLocale();

chooseButton.addEventListener("click", (event) => {
  event.stopPropagation();
  fileInput.click();
});
dropZone.addEventListener("click", () => fileInput.click());
dropZone.addEventListener("keydown", (event) => {
  if (event.key === "Enter" || event.key === " ") {
    event.preventDefault();
    fileInput.click();
  }
});
fileInput.addEventListener("change", () => {
  if (fileInput.files.length) convertFile(fileInput.files[0]);
});

for (const eventName of ["dragenter", "dragover"]) {
  dropZone.addEventListener(eventName, (event) => {
    event.preventDefault();
    dropZone.classList.add("dragover");
  });
}
for (const eventName of ["dragleave", "drop"]) {
  dropZone.addEventListener(eventName, (event) => {
    event.preventDefault();
    dropZone.classList.remove("dragover");
  });
}
dropZone.addEventListener("drop", (event) => {
  const [file] = event.dataTransfer.files;
  if (file) convertFile(file);
});

markdownEditor.addEventListener("input", () => {
  updateCounter();
  scheduleRender();
});
copyButton.addEventListener("click", copyMarkdown);
resetButton.addEventListener("click", resetWorkspace);
downloadButton.addEventListener("click", downloadMarkdown);
document.addEventListener("keydown", (event) => {
  if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "s" && !downloadButton.disabled) {
    event.preventDefault();
    downloadMarkdown();
  }
});

async function convertFile(file) {
  chooseButton.disabled = true;
  fileName.textContent = file.name;
  fileMeta.textContent = t("ready", formatBytes(file.size));
  fileType.textContent = extensionLabel(file.name);

  const formData = new FormData();
  formData.append("file", file);

  try {
    const response = await fetch("/api/convert", { method: "POST", body: formData });
    const payload = await readJson(response);
    if (!response.ok) throw new Error(payload.detail || t("conversionFailed"));

    outputFilename = payload.output_filename || "converted.md";
    markdownEditor.value = payload.markdown || "";
    markdownEditor.disabled = false;
    copyButton.disabled = false;
    resetButton.disabled = false;
    downloadButton.disabled = false;
    fileName.textContent = payload.filename;
    fileMeta.textContent = t("output", formatBytes(payload.source_bytes), Number(payload.elapsed_ms), Number(payload.markdown_chars));
    updateCounter();
    await renderPreview(markdownEditor.value);
    markdownEditor.focus();
  } catch (error) {
    showError(error.message || t("unable"));
    markdownEditor.disabled = true;
    copyButton.disabled = true;
    resetButton.disabled = false;
    downloadButton.disabled = true;
    previewState.textContent = t("failed");
  } finally {
    chooseButton.disabled = false;
    fileInput.value = "";
  }
}

function scheduleRender() {
  window.clearTimeout(renderTimer);
  previewState.textContent = t("updating");
  renderTimer = window.setTimeout(() => renderPreview(markdownEditor.value), 220);
}

async function renderPreview(markdown) {
  const sequence = ++renderSequence;
  try {
    const response = await fetch("/api/render", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ markdown }),
    });
    const payload = await readJson(response);
    if (!response.ok) throw new Error(payload.detail || t("previewFailed"));
    if (sequence !== renderSequence) return;

    markdownPreview.classList.remove("empty");
    markdownPreview.innerHTML = payload.html || `<div class="empty-state"><p>${t("emptyMarkdown")}</p></div>`;
    for (const link of markdownPreview.querySelectorAll("a")) {
      link.target = "_blank";
      link.rel = "noopener noreferrer";
    }
    previewState.textContent = t("synced");
  } catch (error) {
    if (sequence !== renderSequence) return;
    previewState.textContent = t("previewError");
    markdownPreview.classList.add("empty");
    markdownPreview.textContent = error.message || t("previewFailed");
  }
}

async function copyMarkdown() {
  try {
    await navigator.clipboard.writeText(markdownEditor.value);
    const previous = copyButton.textContent;
    copyButton.textContent = t("copied");
    window.setTimeout(() => { copyButton.textContent = previous; }, 1200);
  } catch {
    markdownEditor.select();
    document.execCommand("copy");
  }
}

function downloadMarkdown() {
  const blob = new Blob([markdownEditor.value], { type: "text/markdown;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = outputFilename;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
}

function resetWorkspace() {
  outputFilename = "converted.md";
  markdownEditor.value = "";
  markdownEditor.disabled = true;
  copyButton.disabled = true;
  resetButton.disabled = true;
  downloadButton.disabled = true;
  fileName.textContent = t("notSelected");
  fileMeta.textContent = t("afterConvert");
  fileType.textContent = "MD";
  updateCounter();
  previewState.textContent = t("waiting");
  markdownPreview.classList.add("empty");
  markdownPreview.innerHTML = `<div class="empty-state"><div class="empty-glyph" aria-hidden="true">#</div><p>${t("emptyPreview")}</p></div>`;
}

function showError(message) {
  fileMeta.textContent = message;
}

function updateCounter() {
  charCounter.textContent = `${markdownEditor.value.length.toLocaleString()} ${t("chars")}`;
}

function extensionLabel(name) {
  const extension = name.includes(".") ? name.split(".").pop() : "FILE";
  return extension.slice(0, 5).toUpperCase();
}

function formatBytes(bytes) {
  const value = Number(bytes) || 0;
  if (value < 1024) return `${value} B`;
  if (value < 1024 * 1024) return `${(value / 1024).toFixed(1)} KB`;
  return `${(value / (1024 * 1024)).toFixed(1)} MB`;
}

async function readJson(response) {
  try {
    return await response.json();
  } catch {
    return {};
  }
}
