/** @odoo-module **/

import {getUrl, isImage, photoviewerRenderers} from "@agx_photoviewer/js/photoviewer";
import {deserializeDateTime, formatDateTime} from "@web/core/l10n/dates";
import {EventBus} from "@odoo/owl";
import {_t} from "@web/core/l10n/translation";
import {jsonrpc} from "@web/core/network/rpc_service";
import {loadJS} from "@web/core/assets";
import {session} from "@web/session";

const MODEL = "ir.attachment.annotation";
const PDFJS = "/web/static/lib/pdfjs/build/pdf.js";
const PDFJS_WORKER = "/web/static/lib/pdfjs/build/pdf.worker.js";
const SVG_NS = "http://www.w3.org/2000/svg";
// The drawing layer of a page is 1000 units wide, whatever its size on screen.
const UNITS = 1000;
const COLORS = ["#e53935", "#1e88e5", "#43a047", "#fb8c00", "#212121"];
const ZOOMS = [0.5, 0.75, 1, 1.25, 1.5, 2, 3];

// Sizes are fractions of the page width. Keep the stamps and the constants
// below in sync with pdf_export.py.
const PEN_WIDTH = 0.003;
const STAMP_SIZE = 0.04;
const MIN_BOX = 0.005;
const CHECK_POINTS = [
    [-0.8, 0],
    [-0.25, 0.6],
    [0.85, -0.65],
];
const CROSS_LINES = [
    [
        [-0.7, -0.7],
        [0.7, 0.7],
    ],
    [
        [-0.7, 0.7],
        [0.7, -0.7],
    ],
];
const STAMP_STROKE = 0.14;
const RECT_WIDTH = 0.003;
const PIN_RADIUS = 0.014;
const HIGHLIGHT_OPACITY = 0.35;

const DRAWING_TOOLS = ["pen", "check", "cross", "highlight", "rect", "comment"];

const isPdf = (attachment) => attachment.mimetype === "application/pdf";

const rpcBus = new EventBus();
let rpcId = 0;

function call(method, args, context = {}) {
    return jsonrpc({bus: rpcBus}, rpcId++, `/web/dataset/call_kw/${MODEL}/${method}`, {
        model: MODEL,
        method,
        args,
        kwargs: {context: {...session.user_context, ...context}},
    });
}

function svgElement(tag, attributes = {}) {
    const element = document.createElementNS(SVG_NS, tag);
    for (const [name, value] of Object.entries(attributes)) {
        element.setAttribute(name, value);
    }
    return element;
}

export function htmlElement(tag, className = "", text = "") {
    const element = document.createElement(tag);
    element.className = className;
    element.textContent = text;
    return element;
}

// The annotation each drawn shape stands for.
const shapeAnnotations = new WeakMap();

const round = (value) => Math.round(value * 100000) / 100000;
const clamp = (value) => Math.min(Math.max(value, 0), 1);

// --------------------------------------------------------------------------
// Annotation count badges on the thumbnail strip
// --------------------------------------------------------------------------

const thumbnails = new Map();
let pendingCounts = null;

function setBadge(attachmentId, count) {
    const thumbnail = thumbnails.get(attachmentId);
    if (!thumbnail || !thumbnail.isConnected) {
        return;
    }
    let badge = thumbnail.querySelector(".o_agx_annotation_badge");
    if (!badge) {
        badge = htmlElement("span", "o_agx_annotation_badge");
        thumbnail.append(badge);
    }
    badge.textContent = `✎ ${count}`;
    badge.classList.toggle("d-none", !count);
}

function decorateThumbnail(attachment, thumbnail) {
    thumbnails.set(attachment.id, thumbnail);
    if (!pendingCounts) {
        // One request for the whole strip.
        pendingCounts = new Set();
        Promise.resolve().then(async () => {
            const ids = [...pendingCounts];
            pendingCounts = null;
            // A badge is not worth an error dialog.
            const counts = await call("annotation_counts", [ids]).catch(() => ({}));
            for (const id of ids) {
                setBadge(id, counts[id] || 0);
            }
        });
    }
    pendingCounts.add(attachment.id);
}

// --------------------------------------------------------------------------
// Editor of the annotation layer of one opened file
// --------------------------------------------------------------------------

export class AnnotationEditor {
    constructor(attachment, page) {
        this.attachment = attachment;
        this.page = page;
        this.sheets = [];
        this.annotations = [];
        this.drawing = false;
        this.tool = "pen";
        this.color = COLORS[0];
        this.zoom = 1;
        this.undoStack = [];
        this.session = {added: new Set(), changed: new Set(), removed: 0};
        // Tags every call of this visit (see the Session note).
        this.sessionKey = `${Date.now()}-${Math.random().toString(36).slice(2)}`;
        this.popover = null;
        // The pointer annotating right now: {type, cancel()}.
        this.pointer = null;
        // Fingers on the pages while annotating; two scroll and zoom.
        this.touches = new Map();
        this.gesture = null;
    }

    async start() {
        const [data] = await Promise.all([
            this.call("annotation_load", this.attachment.id),
            this.loadSource(),
        ]);
        if (this.left) {
            // The viewer moved on while the file was loading.
            this.pdf?.destroy();
            return;
        }
        this.checksum = data.checksum;
        this.annotations = data.annotations;
        this.buildDom();
        this.redraw();
    }

    async loadSource() {
        if (isPdf(this.attachment)) {
            await loadJS(PDFJS);
            const pdfjsLib = window.pdfjsLib;
            pdfjsLib.GlobalWorkerOptions.workerSrc = PDFJS_WORKER;
            this.pdf = await pdfjsLib.getDocument({url: getUrl(this.attachment)})
                .promise;
            for (let number = 1; number <= this.pdf.numPages; number++) {
                const pdfPage = await this.pdf.getPage(number);
                // The viewport applies /Rotate: geometry is relative to the
                // page as displayed.
                const viewport = pdfPage.getViewport({scale: 1});
                this.sheets.push({
                    number,
                    pdfPage,
                    baseWidth: viewport.width,
                    ratio: viewport.height / viewport.width,
                });
            }
        } else {
            const image = new Image();
            image.src = getUrl(this.attachment);
            await image.decode();
            this.sheets.push({
                number: 1,
                image,
                ratio: image.naturalHeight / image.naturalWidth || 1,
            });
        }
    }

    // ---------------------------------------------------------------- DOM

    buildDom() {
        this.root = htmlElement("div", "o_agx_annotation");
        this.toolbar = this.buildToolbar();
        this.scroll = htmlElement("div", "o_agx_annotation_scroll");
        // Row holding the pages; extensions may add a side panel to it.
        this.body = htmlElement("div", "o_agx_annotation_body");
        this.body.append(this.scroll);
        this.root.append(this.toolbar);
        const outdated = this.annotations.some(
            (annotation) => annotation.checksum && annotation.checksum !== this.checksum
        );
        if (outdated) {
            this.root.append(
                htmlElement(
                    "div",
                    "o_agx_annotation_warning alert alert-warning m-0 py-1 px-2",
                    _t(
                        "This file was replaced after it was annotated: some marks may be misplaced."
                    )
                )
            );
        }
        this.root.append(this.body);
        // Drawing, typing and scrolling here must not drag the modal or
        // trigger the viewer's shortcuts.
        for (const type of ["mousedown", "touchstart"]) {
            this.root.addEventListener(type, (ev) => ev.stopPropagation(), {
                passive: true,
            });
        }
        // Captured so it runs before a sheet opens the next popover.
        this.scroll.addEventListener(
            "pointerdown",
            (ev) => {
                if (this.popover && !this.popover.contains(ev.target)) {
                    this.closePopover();
                }
            },
            {capture: true}
        );
        for (const type of [
            "pointerdown",
            "pointermove",
            "pointerup",
            "pointercancel",
        ]) {
            this.scroll.addEventListener(type, (ev) => this.onTouch(ev), {
                capture: true,
            });
        }

        this.observer = new IntersectionObserver(
            (entries) => {
                for (const entry of entries) {
                    const sheet = this.sheets.find((s) => s.element === entry.target);
                    sheet.visible = entry.isIntersecting;
                    if (sheet.visible) {
                        this.renderSheet(sheet);
                    }
                }
            },
            {root: this.scroll, rootMargin: "300px"}
        );
        for (const sheet of this.sheets) {
            this.buildSheet(sheet);
            this.scroll.append(sheet.element);
            this.observer.observe(sheet.element);
        }
        let resizeTimer;
        this.resizeObserver = new ResizeObserver(() => {
            clearTimeout(resizeTimer);
            resizeTimer = setTimeout(() => this.renderVisibleSheets(), 200);
        });
        this.resizeObserver.observe(this.scroll);
        this.page.replaceChildren(this.root);
        this.applyZoom();
    }

    buildToolbar() {
        const toolbar = htmlElement("div", "o_agx_annotation_toolbar");
        const button = (icon, title, onClick, text = "") => {
            const element = htmlElement("button", "btn btn-sm btn-light");
            element.type = "button";
            element.title = title;
            element.innerHTML = `<i class="fa ${icon}"></i>`;
            if (text) {
                element.append(htmlElement("span", "ms-1", text));
            }
            element.addEventListener("click", onClick);
            return element;
        };

        this.drawButton = button(
            "fa-pencil-square-o",
            _t("Annotate"),
            () => this.setDrawing(!this.drawing),
            _t("Annotate")
        );
        toolbar.append(this.drawButton);

        this.toolsGroup = htmlElement("div", "o_agx_annotation_tools d-none");
        const tools = [
            ["pen", "fa-pencil", _t("Pen")],
            ["check", "fa-check", _t("Check mark")],
            ["cross", "fa-times", _t("Cross mark")],
            ["highlight", "fa-paint-brush", _t("Highlight")],
            ["rect", "fa-square-o", _t("Rectangle")],
            ["comment", "fa-commenting-o", _t("Comment")],
            ["eraser", "fa-eraser", _t("Erase my marks")],
        ];
        this.toolButtons = {};
        for (const [tool, icon, title] of tools) {
            const element = button(icon, title, () => this.setTool(tool));
            this.toolButtons[tool] = element;
            this.toolsGroup.append(element);
        }
        this.colorButtons = COLORS.map((color) => {
            const element = htmlElement("button", "o_agx_annotation_color");
            element.type = "button";
            element.style.backgroundColor = color;
            element.addEventListener("click", () => this.setColor(color));
            this.toolsGroup.append(element);
            return element;
        });
        this.undoButton = button("fa-undo", _t("Undo my last mark"), () => this.undo());
        this.toolsGroup.append(this.undoButton);
        toolbar.append(this.toolsGroup);

        toolbar.append(htmlElement("div", "flex-grow-1"));
        toolbar.append(
            button("fa-search-minus", _t("Zoom out"), () => this.stepZoom(-1))
        );
        this.zoomLabel = htmlElement("span", "o_agx_annotation_zoom");
        toolbar.append(this.zoomLabel);
        toolbar.append(button("fa-search-plus", _t("Zoom in"), () => this.stepZoom(1)));
        if (this.attachment.mimetype !== "image/svg+xml") {
            toolbar.append(
                button("fa-file-pdf-o", _t("Download with annotations"), () =>
                    this.export()
                )
            );
        }
        this.setTool(this.tool);
        this.setColor(this.color);
        return toolbar;
    }

    buildSheet(sheet) {
        sheet.element = htmlElement("div", "o_agx_annotation_sheet");
        sheet.element.style.aspectRatio = `1 / ${sheet.ratio}`;
        if (sheet.image) {
            sheet.image.className = "o_agx_annotation_source";
            sheet.image.draggable = false;
            sheet.element.append(sheet.image);
        }
        sheet.layer = svgElement("svg", {
            class: "o_agx_annotation_layer",
            viewBox: `0 0 ${UNITS} ${UNITS * sheet.ratio}`,
            preserveAspectRatio: "none",
        });
        sheet.layer.addEventListener("pointerdown", (ev) =>
            this.onPointerDown(ev, sheet)
        );
        sheet.element.append(sheet.layer);
    }

    async renderSheet(sheet) {
        if (!sheet.pdfPage) {
            return;
        }
        const width = Math.round(sheet.element.clientWidth * window.devicePixelRatio);
        if (!width || (sheet.renderedWidth && sheet.renderedWidth >= width * 0.95)) {
            return;
        }
        if (sheet.rendering) {
            sheet.pending = true;
            return;
        }
        sheet.rendering = true;
        try {
            const viewport = sheet.pdfPage.getViewport({
                scale: width / sheet.baseWidth,
            });
            const canvas = htmlElement("canvas", "o_agx_annotation_source");
            canvas.width = Math.round(viewport.width);
            canvas.height = Math.round(viewport.height);
            await sheet.pdfPage.render({
                canvasContext: canvas.getContext("2d"),
                viewport,
            }).promise;
            sheet.canvas?.remove();
            sheet.canvas = canvas;
            sheet.element.prepend(canvas);
            sheet.renderedWidth = width;
        } finally {
            sheet.rendering = false;
        }
        if (sheet.pending) {
            sheet.pending = false;
            this.renderSheet(sheet);
        }
    }

    renderVisibleSheets() {
        for (const sheet of this.sheets) {
            if (sheet.visible) {
                this.renderSheet(sheet);
            }
        }
    }

    // ------------------------------------------------------------ toolbar

    setDrawing(drawing) {
        this.drawing = drawing;
        this.root?.classList.toggle("o_agx_annotation_drawing", drawing);
        this.drawButton.classList.toggle("btn-primary", drawing);
        this.drawButton.classList.toggle("btn-light", !drawing);
        this.toolsGroup.classList.toggle("d-none", !drawing);
        this.updateToolClass();
    }

    setTool(tool) {
        this.tool = tool;
        for (const [name, element] of Object.entries(this.toolButtons)) {
            element.classList.toggle("active", name === tool);
        }
        this.updateToolClass();
    }

    updateToolClass() {
        if (!this.root) {
            return;
        }
        this.root.classList.toggle(
            "o_agx_annotation_tool_draw",
            this.drawing && DRAWING_TOOLS.includes(this.tool)
        );
        this.root.classList.toggle(
            "o_agx_annotation_tool_eraser",
            this.drawing && this.tool === "eraser"
        );
    }

    setColor(color) {
        this.color = color;
        this.colorButtons.forEach((element, index) => {
            element.classList.toggle("active", COLORS[index] === color);
        });
    }

    stepZoom(step) {
        // Pinching leaves the zoom between steps.
        const zooms = step > 0 ? ZOOMS : [...ZOOMS].reverse();
        const zoom = zooms.find((value) => (value - this.zoom) * step > 0.001);
        if (zoom) {
            this.zoom = zoom;
            this.applyZoom();
        }
    }

    applyZoom(render = true) {
        for (const sheet of this.sheets) {
            sheet.element.style.width = `${this.zoom * 100}%`;
        }
        this.zoomLabel.textContent = `${Math.round(this.zoom * 100)}%`;
        if (render) {
            this.renderVisibleSheets();
        }
    }

    export() {
        const link = document.createElement("a");
        link.href = `/agx_photoviewer_annotation/export/${this.attachment.id}`;
        link.click();
    }

    // ------------------------------------------------------------ drawing

    /**
     * Annotations drawn on the pages: the live layer, unless an extension
     * shows another state of it.
     */
    visibleAnnotations() {
        return this.annotations;
    }

    redraw() {
        const annotations = this.visibleAnnotations();
        // A comment drawn twice (e.g. before and after a change) keeps one number.
        const commentIds = new Set(
            annotations
                .filter((annotation) => annotation.kind === "comment")
                .sort((a, b) => a.page - b.page || a.id - b.id)
                .map((comment) => comment.id)
        );
        const numbers = new Map([...commentIds].map((id, index) => [id, index + 1]));
        for (const sheet of this.sheets) {
            sheet.layer.replaceChildren(
                ...annotations
                    .filter((annotation) => annotation.page === sheet.number)
                    .map((annotation) => this.shape(annotation, sheet, numbers))
            );
        }
        setBadge(this.attachment.id, this.annotations.length);
    }

    /**
     * SVG element of `annotation` on `sheet`, in layer units.
     */
    shape(annotation, sheet, numbers) {
        const {geometry, color} = annotation;
        const x = (value) => value * UNITS;
        const y = (value) => value * UNITS * sheet.ratio;
        const group = svgElement("g", {
            class: `o_agx_annotation_shape o_agx_annotation_${annotation.kind}`,
            "data-id": annotation.id || "",
        });
        group.classList.toggle("o_agx_annotation_own", Boolean(annotation.is_own));
        shapeAnnotations.set(group, annotation);
        const stroke = {
            stroke: color,
            fill: "none",
            "stroke-linecap": "round",
            "stroke-linejoin": "round",
        };
        switch (annotation.kind) {
            case "pen": {
                const points = geometry.points
                    .map(([px, py]) => `${x(px)},${y(py)}`)
                    .join(" ");
                const width = x(geometry.width || PEN_WIDTH);
                group.append(
                    // Wider invisible copy so thin strokes are easy to pick.
                    svgElement("polyline", {
                        points,
                        stroke: "transparent",
                        fill: "none",
                        "stroke-width": Math.max(width, 12),
                    }),
                    svgElement("polyline", {points, ...stroke, "stroke-width": width})
                );
                break;
            }
            case "highlight":
            case "rect": {
                const box = {
                    x: x(geometry.x),
                    y: y(geometry.y),
                    width: x(geometry.w),
                    height: y(geometry.h),
                };
                group.append(
                    annotation.kind === "highlight"
                        ? svgElement("rect", {
                              ...box,
                              fill: color,
                              "fill-opacity": HIGHLIGHT_OPACITY,
                          })
                        : svgElement("rect", {
                              ...box,
                              ...stroke,
                              "stroke-width": x(RECT_WIDTH),
                          })
                );
                break;
            }
            case "check":
            case "cross": {
                const radius = x(geometry.size || STAMP_SIZE) / 2;
                const lines =
                    annotation.kind === "check" ? [CHECK_POINTS] : CROSS_LINES;
                const d = lines
                    .map(
                        (line) =>
                            "M" +
                            line
                                .map(
                                    ([px, py]) =>
                                        `${x(geometry.x) + px * radius},${
                                            y(geometry.y) + py * radius
                                        }`
                                )
                                .join("L")
                    )
                    .join("");
                group.append(
                    svgElement("path", {
                        d,
                        ...stroke,
                        "stroke-width": radius * 2 * STAMP_STROKE,
                    })
                );
                break;
            }
            case "comment": {
                const radius = x(PIN_RADIUS);
                group.classList.add("o_agx_annotation_pin");
                group.append(
                    svgElement("circle", {
                        cx: x(geometry.x),
                        cy: y(geometry.y),
                        r: radius,
                        fill: color,
                    })
                );
                const label = svgElement("text", {
                    x: x(geometry.x),
                    y: y(geometry.y),
                    "font-size": radius * 1.2,
                    "text-anchor": "middle",
                    "dominant-baseline": "central",
                });
                label.textContent = numbers.get(annotation.id) || "";
                group.append(label);
                const title = svgElement("title");
                title.textContent = annotation.text;
                group.append(title);
                break;
            }
        }
        return group;
    }

    point(ev, sheet) {
        const rect = sheet.layer.getBoundingClientRect();
        return [
            round(clamp((ev.clientX - rect.left) / rect.width)),
            round(clamp((ev.clientY - rect.top) / rect.height)),
        ];
    }

    onPointerDown(ev, sheet) {
        if (this.gesture || this.pointer) {
            return;
        }
        const target = ev.target.closest(".o_agx_annotation_shape");
        const shown = target && shapeAnnotations.get(target);
        // A mark still being saved cannot be picked yet.
        const annotation = shown?.id ? shown : undefined;
        if (annotation?.kind === "comment") {
            ev.preventDefault();
            if (annotation.is_own && ev.button === 0) {
                this.dragComment(ev, sheet, annotation, target);
            } else {
                this.onTap(ev, () => this.openComment(sheet, annotation));
            }
            return;
        }
        if (!this.drawing) {
            return;
        }
        if (this.tool === "eraser") {
            if (annotation?.is_own) {
                this.onTap(ev, () => this.remove(annotation));
            }
            return;
        }
        if (ev.button !== 0) {
            return;
        }
        ev.preventDefault();
        this.closePopover();
        const [x, y] = this.point(ev, sheet);
        const base = {page: sheet.number, kind: this.tool, color: this.color};
        if (this.tool === "check" || this.tool === "cross") {
            this.onTap(ev, () =>
                this.add({...base, geometry: {x, y, size: STAMP_SIZE}})
            );
            return;
        }
        if (this.tool === "comment") {
            this.onTap(ev, () =>
                this.openComment(sheet, {
                    ...base,
                    geometry: {x, y},
                    text: "",
                    is_own: true,
                })
            );
            return;
        }
        // Pen, highlight and rectangle follow the pointer until it is released.
        const draft = {...base, geometry: {}, is_own: true};
        const points = [[x, y]];
        const update = (moveEv) => {
            if (moveEv.pointerId !== ev.pointerId) {
                return;
            }
            const [mx, my] = this.point(moveEv, sheet);
            if (this.tool === "pen") {
                const [lx, ly] = points[points.length - 1];
                if (Math.hypot(mx - lx, my - ly) > 0.002) {
                    points.push([mx, my]);
                }
                draft.geometry = {points, width: PEN_WIDTH};
            } else {
                draft.geometry = {
                    x: Math.min(x, mx),
                    y: Math.min(y, my),
                    w: round(Math.abs(mx - x)),
                    h: round(Math.abs(my - y)),
                };
            }
            const shape = this.shape(draft, sheet, new Map());
            draftShape.replaceWith(shape);
            draftShape = shape;
        };
        let draftShape = svgElement("g");
        sheet.layer.append(draftShape);
        sheet.layer.setPointerCapture(ev.pointerId);
        const stop = (commit) => {
            sheet.layer.removeEventListener("pointermove", update);
            sheet.layer.removeEventListener("pointerup", finish);
            sheet.layer.removeEventListener("pointercancel", finish);
            if (sheet.layer.hasPointerCapture(ev.pointerId)) {
                sheet.layer.releasePointerCapture(ev.pointerId);
            }
            this.pointer = null;
            draftShape.remove();
            if (!commit) {
                return;
            }
            const {geometry} = draft;
            const valid =
                this.tool === "pen"
                    ? geometry.points?.length > 1
                    : geometry.w > MIN_BOX && geometry.h > MIN_BOX;
            if (valid) {
                this.add({...base, geometry});
            }
        };
        const finish = (upEv) => {
            if (upEv.pointerId === ev.pointerId) {
                stop(upEv.type === "pointerup");
            }
        };
        this.pointer = {type: ev.pointerType, cancel: () => stop(false)};
        sheet.layer.addEventListener("pointermove", update);
        sheet.layer.addEventListener("pointerup", finish);
        sheet.layer.addEventListener("pointercancel", finish);
    }

    // ------------------------------------------------------------ touch

    /**
     * Run `action` once the touch `ev` is lifted without becoming a
     * two-finger gesture; a mouse or a stylus acts at once.
     */
    onTap(ev, action) {
        if (ev.pointerType !== "touch") {
            action();
            return;
        }
        const stop = () => {
            window.removeEventListener("pointerup", finish);
            window.removeEventListener("pointercancel", finish);
            this.pointer = null;
        };
        const finish = (upEv) => {
            if (upEv.pointerId === ev.pointerId) {
                stop();
                if (upEv.type === "pointerup") {
                    action();
                }
            }
        };
        this.pointer = {type: "touch", cancel: stop};
        window.addEventListener("pointerup", finish);
        window.addEventListener("pointercancel", finish);
    }

    /**
     * While annotating, the pages take no native gesture: one finger draws,
     * two scroll and pinch-zoom them. Runs before the pages see the event.
     */
    onTouch(ev) {
        if (ev.pointerType !== "touch") {
            return;
        }
        const position = {x: ev.clientX, y: ev.clientY};
        if (ev.type === "pointerdown") {
            if (!this.drawing) {
                return;
            }
            if (this.pointer && this.pointer.type !== "touch") {
                // A palm resting on the screen while a stylus draws.
                ev.stopPropagation();
                return;
            }
            this.touches.set(ev.pointerId, position);
            if (this.touches.size === 2 && !this.gesture) {
                // The first finger was not drawing after all.
                this.pointer?.cancel();
                this.startGesture();
            }
            if (this.gesture) {
                ev.stopPropagation();
            }
            return;
        }
        if (!this.touches.has(ev.pointerId)) {
            return;
        }
        if (ev.type === "pointermove") {
            this.touches.set(ev.pointerId, position);
            if (this.gesture?.active) {
                this.moveGesture();
            }
            return;
        }
        this.touches.delete(ev.pointerId);
        if (this.gesture?.active && this.touches.size < 2) {
            // The finger left on the screen draws nothing until lifted.
            this.gesture.active = false;
            this.renderVisibleSheets();
        }
        if (!this.touches.size) {
            this.gesture = null;
        }
    }

    startGesture() {
        const [a, b] = this.touches.values();
        this.gesture = {
            active: true,
            zoom: this.zoom,
            distance: Math.hypot(a.x - b.x, a.y - b.y) || 1,
            middle: {x: (a.x + b.x) / 2, y: (a.y + b.y) / 2},
            scrollLeft: this.scroll.scrollLeft,
            scrollTop: this.scroll.scrollTop,
        };
    }

    moveGesture() {
        const gesture = this.gesture;
        const [a, b] = this.touches.values();
        const distance = Math.hypot(a.x - b.x, a.y - b.y);
        const zoom = Math.min(
            Math.max((gesture.zoom * distance) / gesture.distance, ZOOMS[0]),
            ZOOMS[ZOOMS.length - 1]
        );
        const ratio = zoom / gesture.zoom;
        const rect = this.scroll.getBoundingClientRect();
        this.zoom = zoom;
        // Rendered once the fingers are lifted.
        this.applyZoom(false);
        // Keep the point that was between the fingers between them.
        this.scroll.scrollLeft =
            (gesture.scrollLeft + gesture.middle.x - rect.left) * ratio -
            ((a.x + b.x) / 2 - rect.left);
        this.scroll.scrollTop =
            (gesture.scrollTop + gesture.middle.y - rect.top) * ratio -
            ((a.y + b.y) / 2 - rect.top);
    }

    // ------------------------------------------------------------ comments

    /**
     * Move the user's own comment pin while the pointer is down; a click
     * that does not move opens it instead.
     */
    dragComment(ev, sheet, annotation, pin) {
        const [startX, startY] = this.point(ev, sheet);
        const {x, y} = annotation.geometry;
        let geometry = null;
        const move = (moveEv) => {
            if (moveEv.pointerId !== ev.pointerId) {
                return;
            }
            const [mx, my] = this.point(moveEv, sheet);
            if (!geometry && Math.hypot(mx - startX, my - startY) < 0.005) {
                return;
            }
            geometry = {
                x: round(clamp(x + mx - startX)),
                y: round(clamp(y + my - startY)),
            };
            pin.setAttribute(
                "transform",
                `translate(${(geometry.x - x) * UNITS} ${
                    (geometry.y - y) * UNITS * sheet.ratio
                })`
            );
        };
        const stop = () => {
            window.removeEventListener("pointermove", move);
            window.removeEventListener("pointerup", finish);
            window.removeEventListener("pointercancel", finish);
            this.pointer = null;
        };
        const finish = (upEv) => {
            if (upEv.pointerId !== ev.pointerId) {
                return;
            }
            stop();
            if (upEv.type === "pointercancel") {
                pin.removeAttribute("transform");
                return;
            }
            if (!geometry) {
                this.openComment(sheet, annotation);
                return;
            }
            this.update(annotation, {geometry}).catch((error) => {
                this.redraw();
                throw error;
            });
        };
        this.pointer = {
            type: ev.pointerType,
            cancel: () => {
                stop();
                pin.removeAttribute("transform");
            },
        };
        window.addEventListener("pointermove", move);
        window.addEventListener("pointerup", finish);
        window.addEventListener("pointercancel", finish);
    }

    closePopover() {
        this.popover?.remove();
        this.popover = null;
    }

    openComment(sheet, annotation) {
        this.closePopover();
        const popover = htmlElement("div", "o_agx_annotation_popover");
        popover.style.left = `${annotation.geometry.x * 100}%`;
        popover.style.top = `${annotation.geometry.y * 100}%`;
        popover.classList.toggle(
            "o_agx_annotation_popover_left",
            annotation.geometry.x > 0.6
        );
        popover.addEventListener("pointerdown", (ev) => ev.stopPropagation());
        popover.addEventListener("keydown", (ev) => {
            // Keep the viewer's arrow / Escape shortcuts out of the text.
            ev.stopPropagation();
            if (ev.key === "Escape") {
                this.closePopover();
            }
        });
        this.popover = popover;
        sheet.element.append(popover);
        if (annotation.id) {
            this.showComment(annotation);
        } else {
            this.editComment(annotation);
        }
    }

    showComment(annotation) {
        const popover = this.popover;
        const date = formatDateTime(deserializeDateTime(annotation.create_date));
        popover.replaceChildren(
            htmlElement(
                "div",
                "o_agx_annotation_popover_meta",
                `${annotation.author_name} · ${date}`
            ),
            htmlElement("div", "o_agx_annotation_popover_text", annotation.text)
        );
        if (annotation.is_own) {
            const actions = htmlElement("div", "o_agx_annotation_popover_actions");
            const edit = htmlElement("button", "btn btn-sm btn-link p-0", _t("Edit"));
            edit.type = "button";
            edit.addEventListener("click", () => this.editComment(annotation));
            const remove = htmlElement(
                "button",
                "btn btn-sm btn-link text-danger p-0",
                _t("Delete")
            );
            remove.type = "button";
            remove.addEventListener("click", () => {
                this.closePopover();
                this.remove(annotation);
            });
            actions.append(edit, remove);
            popover.append(actions);
        }
    }

    editComment(annotation) {
        const popover = this.popover;
        const textarea = htmlElement("textarea", "form-control form-control-sm");
        textarea.rows = 3;
        textarea.value = annotation.text || "";
        textarea.placeholder = _t("Write a comment...");
        const actions = htmlElement("div", "o_agx_annotation_popover_actions");
        const save = htmlElement("button", "btn btn-sm btn-primary", _t("Save"));
        save.type = "button";
        const cancel = htmlElement("button", "btn btn-sm btn-secondary", _t("Cancel"));
        cancel.type = "button";
        save.addEventListener("click", async () => {
            const text = textarea.value.trim();
            if (!text) {
                return;
            }
            this.closePopover();
            if (annotation.id) {
                await this.update(annotation, {text});
            } else {
                await this.add({...annotation, text});
            }
        });
        cancel.addEventListener("click", () =>
            annotation.id ? this.showComment(annotation) : this.closePopover()
        );
        actions.append(save, cancel);
        popover.replaceChildren(textarea, actions);
        textarea.focus();
    }

    // ------------------------------------------------------------ storage

    call(method, ...args) {
        return call(method, args, {annotation_session: this.sessionKey});
    }

    async add(values) {
        const draft = {...values, is_own: true};
        this.annotations.push(draft);
        this.redraw();
        try {
            const saved = await this.call("annotation_save", {
                attachment_id: this.attachment.id,
                page: values.page,
                kind: values.kind,
                geometry: values.geometry,
                color: values.color,
                text: values.text || false,
            });
            Object.assign(draft, saved);
        } catch (error) {
            this.annotations.splice(this.annotations.indexOf(draft), 1);
            throw error;
        } finally {
            this.redraw();
        }
        this.undoStack.push(draft);
        this.session.added.add(draft.id);
    }

    async update(annotation, values) {
        const saved = await this.call("annotation_save", {
            id: annotation.id,
            ...values,
        });
        Object.assign(annotation, saved);
        if (!this.session.added.has(annotation.id)) {
            this.session.changed.add(annotation.id);
        }
        this.redraw();
    }

    async remove(annotation) {
        await this.call("annotation_delete", annotation.id);
        this.annotations.splice(this.annotations.indexOf(annotation), 1);
        this.undoStack = this.undoStack.filter((a) => a !== annotation);
        if (this.session.added.has(annotation.id)) {
            this.session.added.delete(annotation.id);
        } else {
            this.session.changed.delete(annotation.id);
            this.session.removed++;
        }
        this.redraw();
    }

    undo() {
        const annotation = this.undoStack.pop();
        if (annotation) {
            this.remove(annotation);
        }
    }

    leave() {
        this.left = true;
        this.closePopover();
        this.observer?.disconnect();
        this.resizeObserver?.disconnect();
        this.pdf?.destroy();
        const {added, changed, removed} = this.session;
        if (added.size || changed.size || removed) {
            const commentIds = this.annotations
                .filter(
                    (a) =>
                        a.kind === "comment" && (added.has(a.id) || changed.has(a.id))
                )
                .map((a) => a.id);
            this.call(
                "annotation_session_note",
                this.attachment.id,
                {added: added.size, changed: changed.size, removed},
                commentIds
            );
        }
    }
}

// --------------------------------------------------------------------------

const editors = new WeakMap();

photoviewerRenderers.add(
    "annotation",
    {
        match: (attachment) => isImage(attachment) || isPdf(attachment),
        async render(attachment, page) {
            const editor = new AnnotationEditor(attachment, page);
            editors.set(page, editor);
            await editor.start();
        },
        leave(attachment, page) {
            editors.get(page)?.leave();
            editors.delete(page);
        },
        decorateThumbnail,
    },
    // Before agx_photoviewer_filetypes' PDF renderer.
    {sequence: 10}
);
