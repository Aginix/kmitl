/** @odoo-module **/

import {
    AnnotationEditor,
    htmlElement,
} from "@agx_photoviewer_annotation/js/annotation_renderer";
import {_t} from "@web/core/l10n/translation";
import {patch} from "@web/core/utils/patch";
import {sprintf} from "@web/core/utils/strings";

// Fired on the window once a revision is uploaded, so the chatter and the
// form showing the file catch up (see revision_listener.js).
export const REVISED_EVENT = "agx-attachment-revised";

function button(className, text, onClick) {
    const element = htmlElement("button", `btn btn-sm ${className}`, text);
    element.type = "button";
    element.addEventListener("click", onClick);
    return element;
}

patch(AnnotationEditor.prototype, "agx_photoviewer_annotation_revision", {
    lockedNotice() {
        const revisions = this.data.revisions || [];
        const latest = revisions.find((revision) => revision.latest);
        const current = revisions.find(
            (revision) => revision.id === this.attachment.id
        );
        if (this.data.superseded && latest && current) {
            return sprintf(
                _t("This is revision %s; revision %s replaces it."),
                current.number,
                latest.number
            );
        }
        return this._super(...arguments);
    },

    buildToolbar() {
        const toolbar = this._super(...arguments);
        const revisions = this.data.revisions || [];
        if (revisions.length > 1) {
            const select = htmlElement(
                "select",
                "form-select form-select-sm o_agx_annotation_revisions"
            );
            select.title = _t("Revisions of this file");
            // Latest first.
            for (const revision of [...revisions].reverse()) {
                const option = htmlElement(
                    "option",
                    "",
                    revision.latest
                        ? sprintf(_t("Revision %s (latest)"), revision.number)
                        : sprintf(_t("Revision %s"), revision.number)
                );
                option.value = revision.id;
                option.selected = revision.id === this.attachment.id;
                select.append(option);
            }
            select.addEventListener("change", () =>
                this.showRevision(Number(select.value))
            );
            toolbar.append(select);
        }
        if (this.data.can_revise) {
            this.reviseButton = button("btn-light", "", () =>
                this.chooseRevisionFile()
            );
            this.reviseButton.title = _t("Upload a revision of this file");
            this.reviseButton.innerHTML = '<i class="fa fa-upload"></i>';
            toolbar.append(this.reviseButton);
        }
        return toolbar;
    },

    async showRevision(attachmentId) {
        const revision = (this.data.revisions || []).find((r) => r.id === attachmentId);
        if (revision) {
            await this.switchAttachment({
                id: revision.id,
                name: revision.name,
                mimetype: revision.mimetype,
            });
        }
    },

    chooseRevisionFile() {
        const input = document.createElement("input");
        input.type = "file";
        input.accept = "application/pdf,image/*";
        input.addEventListener("change", () => {
            if (input.files.length) {
                this.uploadRevision(input.files[0]);
            }
        });
        input.click();
    },

    async uploadRevision(file) {
        const body = new FormData();
        body.append("ufile", file);
        body.append("csrf_token", odoo.csrf_token);
        this.reviseButton.disabled = true;
        try {
            const response = await fetch(
                `/agx_photoviewer_annotation_revision/revise/${this.attachment.id}`,
                {method: "POST", body}
            );
            const result = await response.json();
            if (result.error) {
                this.showError(result.error);
                return;
            }
            window.dispatchEvent(new CustomEvent(REVISED_EVENT, {detail: result}));
            await this.switchAttachment(result);
        } finally {
            if (this.reviseButton) {
                this.reviseButton.disabled = false;
            }
        }
    },

    showError(message) {
        const error = this.root.querySelector(".o_agx_annotation_error");
        if (error) {
            error.remove();
        }
        this.body.before(
            htmlElement(
                "div",
                "o_agx_annotation_error alert alert-danger m-0 py-1 px-2",
                message
            )
        );
    },
});
