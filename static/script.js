(function () {
    const dropZone = document.getElementById("drop-zone");
    const fileInput = document.getElementById("file-input");
    const selectBtn = document.getElementById("select-btn");
    const uploadPreview = document.getElementById("upload-preview");
    const resultGrid = document.getElementById("result-grid");
    const resultPlaceholder = document.getElementById("result-placeholder");
    const translateBtn = document.getElementById("translate-btn");
    const langSelect = document.getElementById("lang-select");
    const loadingOverlay = document.getElementById("loading-overlay");
    const loadingText = document.getElementById("loading-text");
    const loadingProgress = document.getElementById("loading-progress");
    const selectAllBtn = document.getElementById("select-all-btn");
    const deselectAllBtn = document.getElementById("deselect-all-btn");
    const batchDownloadBtn = document.getElementById("batch-download-btn");
    const selectedCount = document.getElementById("selected-count");

    const previewModal = document.getElementById("preview-modal");
    const previewImage = document.getElementById("preview-image");
    const previewClose = document.getElementById("preview-close");
    const previewDownload = document.getElementById("preview-download");

    let uploadedFiles = [];
    let resultItems = [];

    const langLabels = {
        en: "英语", vi: "越南语", fr: "法语",
        de: "德语", th: "泰语", id: "印尼语", ja: "日语",
    };

    selectBtn.addEventListener("click", (e) => {
        e.stopPropagation();
        fileInput.click();
    });

    dropZone.addEventListener("click", (e) => {
        if (e.target === selectBtn || selectBtn.contains(e.target)) return;
        fileInput.click();
    });

    fileInput.addEventListener("change", (e) => handleFiles(e.target.files));

    dropZone.addEventListener("dragover", (e) => {
        e.preventDefault();
        dropZone.classList.add("dragover");
    });
    dropZone.addEventListener("dragleave", () => dropZone.classList.remove("dragover"));
    dropZone.addEventListener("drop", (e) => {
        e.preventDefault();
        dropZone.classList.remove("dragover");
        handleFiles(e.dataTransfer.files);
    });

    translateBtn.addEventListener("click", startTranslate);

    previewClose.addEventListener("click", closePreview);
    previewModal.querySelector(".preview-modal-backdrop").addEventListener("click", closePreview);
    document.addEventListener("keydown", (e) => {
        if (e.key === "Escape") closePreview();
    });

    selectAllBtn.addEventListener("click", () => {
        document.querySelectorAll(".result-checkbox").forEach(cb => cb.checked = true);
        updateSelectedCount();
    });

    deselectAllBtn.addEventListener("click", () => {
        document.querySelectorAll(".result-checkbox").forEach(cb => cb.checked = false);
        updateSelectedCount();
    });

    function updateSelectedCount() {
        const checked = document.querySelectorAll(".result-checkbox:checked").length;
        const total = document.querySelectorAll(".result-checkbox").length;
        selectedCount.textContent = `已选 ${checked}/${total}`;
        batchDownloadBtn.disabled = checked === 0;
    }

    function handleFiles(files) {
        for (const file of files) {
            if (!file.type.startsWith("image/")) continue;
            const id = Date.now() + "-" + Math.random().toString(36).slice(2, 8);
            const url = URL.createObjectURL(file);
            uploadedFiles.push({ file, id, url });
        }
        renderUploadPreviews();
        translateBtn.disabled = uploadedFiles.length === 0;
        fileInput.value = "";
    }

    function renderUploadPreviews() {
        uploadPreview.innerHTML = "";
        uploadedFiles.forEach((item) => {
            const card = document.createElement("div");
            card.className = "preview-card";
            card.innerHTML = `
                <img src="${item.url}" alt="原图">
                <button class="remove-btn" data-id="${item.id}" title="移除">&#x2715;</button>
            `;
            uploadPreview.appendChild(card);
        });

        uploadPreview.querySelectorAll(".remove-btn").forEach((btn) => {
            btn.addEventListener("click", (e) => {
                e.stopPropagation();
                const id = btn.dataset.id;
                const item = uploadedFiles.find((f) => f.id === id);
                if (item) URL.revokeObjectURL(item.url);
                uploadedFiles = uploadedFiles.filter((f) => f.id !== id);
                renderUploadPreviews();
                translateBtn.disabled = uploadedFiles.length === 0;
            });
        });
    }

    async function startTranslate() {
        if (uploadedFiles.length === 0) return;

        const lang = langSelect.value;
        showLoading(`正在翻译为${langLabels[lang] || lang}...`, `共 ${uploadedFiles.length} 张图片`);

        const formData = new FormData();
        uploadedFiles.forEach((item) => formData.append("files", item.file));
        formData.append("lang", lang);

        try {
            const resp = await fetch("/api/translate", { method: "POST", body: formData });
            const data = await resp.json();

            if (data.error) {
                hideLoading();
                alert("错误: " + data.error);
                return;
            }

            renderResults(data.results);
        } catch (err) {
            hideLoading();
            alert("请求失败: " + err.message);
        }
    }

    function renderResults(results) {
        resultGrid.innerHTML = "";
        resultPlaceholder.style.display = "none";
        resultGrid.style.display = "grid";
        document.getElementById("batch-bar").classList.add("show");
        resultItems = [];

        const lang = langSelect.value;
        const langLabel = langLabels[lang] || lang;

        results.forEach((r) => {
            const card = document.createElement("div");
            card.className = "preview-card";
            card.innerHTML = `
                <label class="checkbox-label">
                    <input type="checkbox" class="result-checkbox" data-src="${r.translated}" checked>
                </label>
                <img src="${r.translated}" alt="译文" class="result-thumb" data-src="${r.translated}">
                <div class="card-info">
                    <span class="lang-tag">${langLabel}</span>
                    ${r.translations > 0 ? `<span>${r.translations} 处翻译</span>` : "<span>无中文</span>"}
                </div>
                <div class="card-actions">
                    <button class="preview-btn" data-src="${r.translated}">预览</button>
                    <a class="download-btn" href="${r.translated}" download>下载</a>
                    <button class="remove-result-btn" data-src="${r.translated}" title="删除">&#x2715;</button>
                </div>
            `;
            resultGrid.appendChild(card);
            resultItems.push({ card, translated: r.translated });
        });

        resultGrid.querySelectorAll(".result-thumb").forEach((img) => {
            img.addEventListener("click", () => openPreview(img.dataset.src));
        });
        resultGrid.querySelectorAll(".preview-btn").forEach((btn) => {
            btn.addEventListener("click", () => openPreview(btn.dataset.src));
        });
        resultGrid.querySelectorAll(".remove-result-btn").forEach((btn) => {
            btn.addEventListener("click", (e) => {
                e.stopPropagation();
                const item = resultItems.find((i) => i.translated === btn.dataset.src);
                if (item) {
                    item.card.remove();
                    resultItems = resultItems.filter((i) => i !== item);
                    if (resultItems.length === 0) {
                        resultGrid.style.display = "none";
                        resultPlaceholder.style.display = "flex";
                    }
                    updateSelectedCount();
                }
            });
        });

        resultGrid.querySelectorAll(".result-checkbox").forEach((cb) => {
            cb.addEventListener("change", updateSelectedCount);
        });

        hideLoading();
        uploadedFiles.forEach((item) => URL.revokeObjectURL(item.url));
        uploadedFiles = [];
        uploadPreview.innerHTML = "";
        translateBtn.disabled = true;
        updateSelectedCount();
    }

    // 批量下载
    batchDownloadBtn.addEventListener("click", () => {
        const checked = document.querySelectorAll(".result-checkbox:checked");
        if (checked.length === 0) return;

        checked.forEach((cb) => {
            const a = document.createElement("a");
            a.href = cb.dataset.src;
            a.download = "";
            a.click();
        });
    });

    function openPreview(src) {
        previewImage.src = src;
        previewDownload.href = src;
        previewModal.style.display = "flex";
        document.body.style.overflow = "hidden";
    }

    function closePreview() {
        previewModal.style.display = "none";
        document.body.style.overflow = "";
        previewImage.src = "";
    }

    function showLoading(text, progress) {
        loadingText.textContent = text;
        loadingProgress.textContent = progress || "";
        loadingOverlay.style.display = "flex";
    }

    function hideLoading() {
        loadingOverlay.style.display = "none";
    }
})();
