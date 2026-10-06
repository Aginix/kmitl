/** @odoo-module **/

import {
    getExtension,
    getUrl,
    photoviewerRenderers,
} from "@agx_photoviewer/js/photoviewer";
import {loadJS} from "@web/core/assets";

const LIB = "/agx_photoviewer_filetypes/static/lib";
const PDFJS_VIEWER = "/web/static/lib/pdfjs/web/viewer.html?file=";
// Rows read per sheet; keeps huge workbooks from freezing the browser.
const MAX_SHEET_ROWS = 5000;
const SLIDE_WIDTH = 960;

const matchFile = (mimetypes, extensions) => (attachment) =>
    mimetypes.includes(attachment.mimetype) ||
    extensions.includes(getExtension(attachment));

async function fetchArrayBuffer(attachment) {
    const response = await fetch(getUrl(attachment));
    if (!response.ok) {
        throw new Error(`Cannot fetch attachment ${attachment.id}: ${response.status}`);
    }
    return response.arrayBuffer();
}

function renderPdf(attachment, page) {
    const iframe = document.createElement("iframe");
    iframe.src = `${PDFJS_VIEWER}${encodeURIComponent(
        getUrl(attachment)
    )}#pagemode=none`;
    page.replaceChildren(iframe);
}

function renderVideo(attachment, page) {
    const video = document.createElement("video");
    video.className = "o_agx_photoviewer_video";
    video.controls = true;
    video.src = getUrl(attachment);
    page.replaceChildren(video);
}

async function renderDocx(attachment, page) {
    await loadJS(`${LIB}/jszip/jszip.min.js`);
    await loadJS(`${LIB}/docx-preview/docx-preview.min.js`);
    const data = await fetchArrayBuffer(attachment);
    await window.docx.renderAsync(data, page);
}

async function renderXlsx(attachment, page) {
    await loadJS(`${LIB}/xlsx/xlsx.full.min.js`);
    const data = await fetchArrayBuffer(attachment);
    const workbook = window.XLSX.read(data, {type: "array", sheetRows: MAX_SHEET_ROWS});

    const tabs = document.createElement("div");
    tabs.className = "o_agx_photoviewer_sheet_tabs btn-group";
    const sheet = document.createElement("div");
    sheet.className = "o_agx_photoviewer_sheet";
    const showSheet = (name) => {
        const html = window.XLSX.utils.sheet_to_html(workbook.Sheets[name], {
            header: "",
            footer: "",
        });
        // Cell texts are escaped by SheetJS; only keep harmless hyperlinks.
        const template = document.createElement("template");
        template.innerHTML = html;
        for (const link of template.content.querySelectorAll("a")) {
            if (/^(https?:|mailto:)/i.test(link.getAttribute("href"))) {
                link.target = "_blank";
                link.rel = "noopener noreferrer";
            } else {
                link.removeAttribute("href");
            }
        }
        sheet.replaceChildren(template.content);
        for (const tab of tabs.children) {
            tab.classList.toggle("active", tab.textContent === name);
        }
    };
    for (const name of workbook.SheetNames) {
        const tab = document.createElement("button");
        tab.type = "button";
        tab.className = "btn btn-sm btn-outline-primary";
        tab.textContent = name;
        tab.addEventListener("click", () => showSheet(name));
        tabs.append(tab);
    }

    const wrapper = document.createElement("div");
    wrapper.className = "o_agx_photoviewer_sheets";
    wrapper.append(tabs, sheet);
    page.replaceChildren(wrapper);
    showSheet(workbook.SheetNames[0]);
}

/**
 * Some generators list parts that are not in the zip in [Content_Types].xml;
 * pptx-preview then silently loads zero slides. Drop those entries and read
 * the slide size while the archive is open.
 */
async function readPptx(attachment) {
    await loadJS(`${LIB}/jszip/jszip.min.js`);
    let data = await fetchArrayBuffer(attachment);
    const zip = await window.JSZip.loadAsync(data);
    const types = new DOMParser().parseFromString(
        await zip.file("[Content_Types].xml").async("text"),
        "application/xml"
    );
    let dirty = false;
    // Copy the live collection: removing entries while iterating it skips some.
    for (const override of [...types.getElementsByTagName("Override")]) {
        if (!zip.file(override.getAttribute("PartName").slice(1))) {
            override.remove();
            dirty = true;
        }
    }
    if (dirty) {
        zip.file("[Content_Types].xml", new XMLSerializer().serializeToString(types));
        data = await zip.generateAsync({type: "arraybuffer", compression: "STORE"});
    }
    const presentation = new DOMParser().parseFromString(
        await zip.file("ppt/presentation.xml").async("text"),
        "application/xml"
    );
    const size = presentation.getElementsByTagNameNS("*", "sldSz")[0];
    const ratio = size ? size.getAttribute("cy") / size.getAttribute("cx") : 9 / 16;
    return {data, ratio};
}

async function renderPptx(attachment, page) {
    await loadJS(`${LIB}/pptx-preview/pptx-preview.umd.js`);
    const {data, ratio} = await readPptx(attachment);
    const wrapper = document.createElement("div");
    page.replaceChildren(wrapper);
    const previewer = window.pptxPreview.init(wrapper, {
        width: SLIDE_WIDTH,
        height: Math.round(SLIDE_WIDTH * ratio),
    });
    const pptx = await previewer.preview(data);
    if (!pptx.slides.length) {
        throw new Error(`No slide found in attachment ${attachment.id}`);
    }
    // The slides are laid out at a fixed width: scale them to the page, which
    // follows the (freely resizable) modal.
    const reader = wrapper.firstElementChild;
    const fit = () => {
        const zoom = page.clientWidth / SLIDE_WIDTH;
        reader.style.zoom = zoom;
        reader.style.height = `${page.clientHeight / zoom}px`;
    };
    fit();
    new ResizeObserver(fit).observe(page);
}

const renderers = {
    pdf: {
        match: matchFile(["application/pdf"], ["pdf"]),
        render: renderPdf,
    },
    video: {
        match: matchFile(
            ["video/mp4", "video/webm", "video/ogg"],
            ["mp4", "webm", "ogv"]
        ),
        render: renderVideo,
    },
    docx: {
        match: matchFile(
            ["application/vnd.openxmlformats-officedocument.wordprocessingml.document"],
            ["docx"]
        ),
        render: renderDocx,
    },
    xlsx: {
        match: matchFile(
            [
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                "application/vnd.ms-excel",
            ],
            ["xlsx", "xlsm", "xls"]
        ),
        render: renderXlsx,
    },
    pptx: {
        match: matchFile(
            [
                "application/vnd.openxmlformats-officedocument.presentationml.presentation",
            ],
            ["pptx"]
        ),
        render: renderPptx,
    },
};
for (const [name, renderer] of Object.entries(renderers)) {
    photoviewerRenderers.add(name, renderer);
}
