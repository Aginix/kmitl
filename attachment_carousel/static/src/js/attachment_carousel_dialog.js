/** @odoo-module **/

import { Dialog } from "@web/core/dialog/dialog";

const { Component, useState, onMounted, onWillUnmount } = owl;

// Keep in sync with attachment_carousel/models/ir_attachment.py::OFFICE_MIMETYPES.
// This drives the frontend routing decision: office mimetypes hit the
// server-side LibreOffice preview endpoint; images and PDFs render directly.
const OFFICE_MIMETYPES = new Set([
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "application/msword",
    "application/vnd.ms-excel",
    "application/vnd.ms-powerpoint",
    "application/vnd.oasis.opendocument.text",
    "application/vnd.oasis.opendocument.spreadsheet",
    "application/vnd.oasis.opendocument.presentation",
    "application/rtf",
    "text/rtf",
    "text/csv",
]);

export class AttachmentCarouselDialog extends Component {
    setup() {
        const startIndex = Math.min(
            Math.max(this.props.startIndex || 0, 0),
            Math.max(this.props.attachments.length - 1, 0)
        );
        this.state = useState({ index: startIndex });

        this._onKeydown = this.onKeydown.bind(this);
        onMounted(() => document.addEventListener("keydown", this._onKeydown));
        onWillUnmount(() => document.removeEventListener("keydown", this._onKeydown));
    }

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

    isOffice(att) {
        return !!(att && OFFICE_MIMETYPES.has(att.mimetype));
    }

    isIframable(att) {
        return this.isPdf(att) || this.isOffice(att);
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
        if (this.isOffice(att)) {
            return `/attachment_carousel/preview/${att.id}#toolbar=1&navpanes=0`;
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
        if (att.mimetype.includes("excel") || att.mimetype.includes("spreadsheet") || att.mimetype === "text/csv") {
            return "fa-file-excel-o";
        }
        if (att.mimetype.includes("powerpoint") || att.mimetype.includes("presentation")) {
            return "fa-file-powerpoint-o";
        }
        return "fa-file-o";
    }

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
}

AttachmentCarouselDialog.template = "attachment_carousel.Dialog";
AttachmentCarouselDialog.components = { Dialog };
AttachmentCarouselDialog.props = {
    attachments: { type: Array },
    startIndex: { type: Number, optional: true },
    title: { type: String, optional: true },
    close: { type: Function },
};
