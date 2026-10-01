/** @odoo-module **/

import { Dialog } from "@web/core/dialog/dialog";

const { Component, useState, useRef, useEffect, onMounted, onWillUnmount, markup } = owl;

const DOCX_MIMETYPES = new Set([
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
]);
const XLSX_MIMETYPES = new Set([
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.ms-excel",
    "text/csv",
]);
const PPTX_MIMETYPES = new Set([
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
]);

// Lazy-load JS/CSS once per browser session. Each URL resolves to a shared
// Promise so switching slides never fetches the same lib twice.
const _loadedScripts = new Map();
const _loadedStylesheets = new Map();

function loadScript(url) {
    if (_loadedScripts.has(url)) {
        return _loadedScripts.get(url);
    }
    const p = new Promise((resolve, reject) => {
        const s = document.createElement("script");
        s.src = url;
        s.async = false; // preserve execution order across sequential loadScript calls
        s.onload = () => resolve();
        s.onerror = () => reject(new Error(`Failed to load script: ${url}`));
        document.head.appendChild(s);
    });
    _loadedScripts.set(url, p);
    return p;
}

function loadStylesheet(url) {
    if (_loadedStylesheets.has(url)) {
        return _loadedStylesheets.get(url);
    }
    const p = new Promise((resolve, reject) => {
        const l = document.createElement("link");
        l.rel = "stylesheet";
        l.href = url;
        l.onload = () => resolve();
        l.onerror = () => reject(new Error(`Failed to load stylesheet: ${url}`));
        document.head.appendChild(l);
    });
    _loadedStylesheets.set(url, p);
    return p;
}

async function loadScriptsSerial(urls) {
    for (const url of urls) {
        await loadScript(url);
    }
}

const LIB = {
    MAMMOTH: "/attachment_carousel/static/lib/mammoth.browser.min.js",
    XLSX: "/attachment_carousel/static/lib/xlsx.full.min.js",
    PPTX_SCRIPTS: [
        "/attachment_carousel/static/lib/pptxjs/jquery.slim.min.js",
        "/attachment_carousel/static/lib/pptxjs/jszip.min.js",
        "/attachment_carousel/static/lib/pptxjs/FileSaver.min.js",
        "/attachment_carousel/static/lib/pptxjs/d3.min.js",
        "/attachment_carousel/static/lib/pptxjs/nvd3.min.js",
        "/attachment_carousel/static/lib/pptxjs/divs2slides.js",
        "/attachment_carousel/static/lib/pptxjs/pptxjs.js",
    ],
    PPTX_STYLES: [
        "/attachment_carousel/static/lib/pptxjs/pptxjs.css",
        "/attachment_carousel/static/lib/pptxjs/nv.d3.min.css",
    ],
};

export class AttachmentCarouselDialog extends Component {
    setup() {
        const startIndex = Math.min(
            Math.max(this.props.startIndex || 0, 0),
            Math.max(this.props.attachments.length - 1, 0)
        );
        this.state = useState({
            index: startIndex,
            loading: false,
            error: null,
            htmlPreview: null,
            sheets: null,
            activeSheet: 0,
            // Bumped on every index change to force the pptx container to
            // remount — PPTXjs manipulates DOM directly and does not clean up
            // after itself, so a fresh element is simpler than tearing down.
            renderKey: 0,
        });

        // Reference to the pptx container div so we can hand it to jQuery.
        this.pptxContainer = useRef("pptxContainer");

        // Trigger (re)render whenever the current attachment changes.
        useEffect(
            () => {
                this._renderCurrent();
            },
            () => [this.state.index]
        );

        this._onKeydown = this.onKeydown.bind(this);
        onMounted(() => document.addEventListener("keydown", this._onKeydown));
        onWillUnmount(() => document.removeEventListener("keydown", this._onKeydown));
    }

    // ------------------------------------------------------------------
    // Classifiers
    // ------------------------------------------------------------------
    get current() {
        return this.props.attachments[this.state.index];
    }

    get count() {
        return this.props.attachments.length;
    }

    get dialogTitle() {
        const base = this.props.title || this.env._t("Attachments");
        if (!this.count) {
            return base;
        }
        return `${base} — ${this.state.index + 1} / ${this.count}`;
    }

    isImage(att) {
        return !!(att && att.mimetype && att.mimetype.startsWith("image/"));
    }

    isPdf(att) {
        return !!(att && att.mimetype === "application/pdf");
    }

    isDocx(att) {
        return !!(att && DOCX_MIMETYPES.has(att.mimetype));
    }

    isXlsx(att) {
        return !!(att && XLSX_MIMETYPES.has(att.mimetype));
    }

    isPptx(att) {
        return !!(att && PPTX_MIMETYPES.has(att.mimetype));
    }

    contentUrl(att) {
        if (!att) {
            return "#";
        }
        if (this.isImage(att)) {
            return `/web/image/${att.id}`;
        }
        if (this.isPdf(att)) {
            return `/web/content/${att.id}?download=false#toolbar=1&navpanes=0`;
        }
        return `/web/content/${att.id}?download=true`;
    }

    thumbnailUrl(att) {
        if (this.isImage(att)) {
            return `/web/image/${att.id}/100x100`;
        }
        return null;
    }

    fileIcon(att) {
        if (this.isPdf(att)) {
            return "fa-file-pdf-o";
        }
        if (!att || !att.mimetype) {
            return "fa-file-o";
        }
        if (att.mimetype.includes("word") || att.mimetype.includes("opendocument.text")) {
            return "fa-file-word-o";
        }
        if (
            att.mimetype.includes("excel") ||
            att.mimetype.includes("spreadsheet") ||
            att.mimetype === "text/csv"
        ) {
            return "fa-file-excel-o";
        }
        if (att.mimetype.includes("powerpoint") || att.mimetype.includes("presentation")) {
            return "fa-file-powerpoint-o";
        }
        return "fa-file-o";
    }

    // ------------------------------------------------------------------
    // Navigation
    // ------------------------------------------------------------------
    next() {
        if (this.count > 1) {
            this.state.index = (this.state.index + 1) % this.count;
        }
    }

    prev() {
        if (this.count > 1) {
            this.state.index = (this.state.index - 1 + this.count) % this.count;
        }
    }

    goTo(i) {
        if (i >= 0 && i < this.count) {
            this.state.index = i;
        }
    }

    setSheet(i) {
        this.state.activeSheet = i;
    }

    download() {
        if (this.current) {
            window.open(`/web/content/${this.current.id}?download=true`, "_blank");
        }
    }

    onKeydown(ev) {
        if (ev.key === "ArrowRight") {
            this.next();
            ev.preventDefault();
        } else if (ev.key === "ArrowLeft") {
            this.prev();
            ev.preventDefault();
        }
    }

    // ------------------------------------------------------------------
    // Client-side renderers
    // ------------------------------------------------------------------
    _resetPreview() {
        this.state.loading = false;
        this.state.error = null;
        this.state.htmlPreview = null;
        this.state.sheets = null;
        this.state.activeSheet = 0;
        this.state.renderKey += 1;
    }

    async _renderCurrent() {
        this._resetPreview();
        const att = this.current;
        if (!att) {
            return;
        }
        try {
            if (this.isDocx(att)) {
                await this._renderDocx(att);
            } else if (this.isXlsx(att)) {
                await this._renderXlsx(att);
            } else if (this.isPptx(att)) {
                await this._renderPptx(att);
            }
        } catch (e) {
            // Guard against race when user clicks next before render finishes.
            if (att !== this.current) {
                return;
            }
            // eslint-disable-next-line no-console
            console.warn("[attachment_carousel] preview failed:", e);
            this.state.loading = false;
            this.state.error = (e && e.message) || String(e);
        }
    }

    async _fetchArrayBuffer(att) {
        const res = await fetch(`/web/content/${att.id}`, { credentials: "same-origin" });
        if (!res.ok) {
            throw new Error(`HTTP ${res.status}`);
        }
        return await res.arrayBuffer();
    }

    async _renderDocx(att) {
        this.state.loading = true;
        await loadScript(LIB.MAMMOTH);
        const buf = await this._fetchArrayBuffer(att);
        if (att !== this.current) {
            return;
        }
        const result = await window.mammoth.convertToHtml({ arrayBuffer: buf });
        if (att !== this.current) {
            return;
        }
        this.state.htmlPreview = markup(result.value || "");
        this.state.loading = false;
    }

    async _renderXlsx(att) {
        this.state.loading = true;
        await loadScript(LIB.XLSX);
        const buf = await this._fetchArrayBuffer(att);
        if (att !== this.current) {
            return;
        }
        const wb = window.XLSX.read(buf, { type: "array" });
        if (att !== this.current) {
            return;
        }
        const sheets = wb.SheetNames.map((name) => ({
            name,
            html: markup(window.XLSX.utils.sheet_to_html(wb.Sheets[name])),
        }));
        this.state.sheets = sheets;
        this.state.activeSheet = 0;
        this.state.loading = false;
    }

    async _renderPptx(att) {
        this.state.loading = true;
        await Promise.all(LIB.PPTX_STYLES.map(loadStylesheet));
        await loadScriptsSerial(LIB.PPTX_SCRIPTS);
        if (att !== this.current) {
            return;
        }
        // Yield so OWL can mount the fresh container keyed on renderKey.
        await Promise.resolve();
        const el = this.pptxContainer.el;
        if (!el || att !== this.current) {
            return;
        }
        const $ = window.jQuery || window.$;
        if (!$ || !$.fn.pptxToHtml) {
            throw new Error("PPTXjs failed to load");
        }
        // PPTXjs fetches the pptx itself; let it hit the standard download URL.
        $(el).pptxToHtml({
            pptxFileUrl: `/web/content/${att.id}?download=true`,
            slidesScale: "80%",
            slideMode: false,
            keyBoardShortCut: false,
        });
        this.state.loading = false;
    }
}

AttachmentCarouselDialog.template = "attachment_carousel.Dialog";
AttachmentCarouselDialog.components = { Dialog };
AttachmentCarouselDialog.props = {
    attachments: { type: Array },
    startIndex: { type: Number, optional: true },
    title: { type: String, optional: true },
    close: { type: Function },
};
