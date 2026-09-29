/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

const { Component, useState, onWillStart, onMounted, onWillUnmount } = owl;

export class DisbursementAttachmentCarousel extends Component {
    setup() {
        this.orm = useService("orm");
        this.actionService = useService("action");
        this.params = (this.props.action && this.props.action.params) || {};
        this.state = useState({
            attachments: [],
            index: 0,
            loading: true,
        });

        onWillStart(async () => {
            const resId = this.params.res_id;
            if (!resId) {
                this.state.loading = false;
                return;
            }
            const atts = await this.orm.searchRead(
                "ir.attachment",
                [
                    ["res_model", "=", "disbursement.request"],
                    ["res_id", "=", resId],
                ],
                ["id", "name", "mimetype", "file_size"],
                { order: "id asc" }
            );
            this.state.attachments = atts;
            this.state.loading = false;
        });

        this._onKeydown = this.onKeydown.bind(this);
        onMounted(() => document.addEventListener("keydown", this._onKeydown));
        onWillUnmount(() => document.removeEventListener("keydown", this._onKeydown));
    }

    get current() {
        return this.state.attachments[this.state.index];
    }

    get count() {
        return this.state.attachments.length;
    }

    isImage(att) {
        return !!(att && att.mimetype && att.mimetype.startsWith("image/"));
    }

    isPdf(att) {
        return !!(att && att.mimetype === "application/pdf");
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

DisbursementAttachmentCarousel.template = "disbursement_attachment_carousel.AttachmentCarousel";

registry
    .category("actions")
    .add("disbursement_attachment_carousel", DisbursementAttachmentCarousel);
