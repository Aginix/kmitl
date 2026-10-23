/** @odoo-module **/

import {
    AnnotationEditor,
    htmlElement,
} from "@agx_photoviewer_annotation/js/annotation_renderer";
import {deserializeDateTime, formatDateTime} from "@web/core/l10n/dates";
import {_t} from "@web/core/l10n/translation";
import {patch} from "@web/core/utils/patch";
import {sprintf} from "@web/core/utils/strings";

function stateLabel(state) {
    return (
        {
            open: _t("Open"),
            answered: _t("Answered"),
            closed: _t("Closed"),
        }[state] || ""
    );
}

function button(className, text, onClick) {
    const element = htmlElement("button", `btn btn-sm ${className}`, text);
    element.type = "button";
    element.addEventListener("click", onClick);
    return element;
}

patch(AnnotationEditor.prototype, "agx_photoviewer_annotation_review", {
    reset() {
        this._super(...arguments);
        this.requestCheckbox = null;
    },

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

    // ------------------------------------------------------------ toolbar

    buildToolbar() {
        const toolbar = this._super(...arguments);
        const revisions = this.data.revisions || [];
        if (revisions.length > 1) {
            const select = htmlElement(
                "select",
                "form-select form-select-sm o_agx_annotation_revisions"
            );
            select.title = _t("Revisions of this file");
            for (const revision of revisions) {
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
        this.requestsButton = button("btn-light", "", () => this.toggleRequests());
        this.requestsButton.title = _t("Change requests");
        toolbar.append(this.requestsButton);
        return toolbar;
    },

    buildDom() {
        this._super(...arguments);
        this.requestsPanel = htmlElement("div", "o_agx_annotation_requests");
        this.body.append(this.requestsPanel);
        // Open by default when some are waiting; kept across revisions.
        if (this.requestsOpen === undefined) {
            this.requestsOpen = Boolean(this.data.requests?.length);
        }
        this.renderRequests();
    },

    // ------------------------------------------------------------ marks

    shape(annotation) {
        const group = this._super(...arguments);
        if (annotation.change_request) {
            group.classList.add(
                "o_agx_annotation_request",
                `o_agx_annotation_request_${annotation.request_state}`
            );
        }
        return group;
    },

    annotationValues(values) {
        const result = this._super(...arguments);
        if (values.kind === "comment") {
            result.change_request = Boolean(values.change_request);
        }
        return result;
    },

    editComment(annotation) {
        this._super(...arguments);
        const label = htmlElement("label", "o_agx_annotation_request_toggle");
        const checkbox = htmlElement("input");
        checkbox.type = "checkbox";
        // A plain Comment unless the reviewer asks for a fix.
        checkbox.checked = Boolean(annotation.change_request);
        label.append(checkbox, htmlElement("span", "ms-1", _t("Ask for a fix")));
        this.popover.querySelector(".o_agx_annotation_popover_actions").before(label);
        this.requestCheckbox = checkbox;
    },

    commentFormValues() {
        const values = this._super(...arguments);
        if (this.requestCheckbox) {
            values.change_request = this.requestCheckbox.checked;
        }
        return values;
    },

    showComment(annotation) {
        this._super(...arguments);
        if (annotation.change_request) {
            this.popover.append(this.requestDetails(annotation));
        }
    },

    add() {
        return this.refreshRequestsAfter(this._super(...arguments));
    },

    update() {
        return this.refreshRequestsAfter(this._super(...arguments));
    },

    remove() {
        return this.refreshRequestsAfter(this._super(...arguments));
    },

    // ------------------------------------------------------------ requests

    async refreshRequestsAfter(promise) {
        const result = await promise;
        // The requests of this revision come from its layer, the others
        // from the server.
        this.data.requests = [
            ...(this.data.requests || []).filter(
                (request) => request.attachment_id !== this.attachment.id
            ),
            ...this.annotations.filter(
                (annotation) =>
                    annotation.change_request && annotation.request_state !== "closed"
            ),
        ];
        this.renderRequests();
        return result;
    },

    /**
     * Status, Response and actions of the Change request `request`.
     */
    requestDetails(request) {
        const details = htmlElement("div", "o_agx_annotation_request_details");
        details.append(
            htmlElement(
                "span",
                `o_agx_annotation_request_state o_agx_annotation_request_${request.request_state}`,
                `${_t("Change request")} · ${stateLabel(request.request_state)}`
            )
        );
        if (request.response) {
            const date = request.response_date
                ? ` · ${formatDateTime(deserializeDateTime(request.response_date))}`
                : "";
            details.append(
                htmlElement(
                    "div",
                    "o_agx_annotation_popover_meta mt-1",
                    `${request.response_name}${date}`
                ),
                htmlElement("div", "o_agx_annotation_popover_text", request.response)
            );
        }
        const actions = htmlElement("div", "o_agx_annotation_popover_actions");
        details.append(actions);
        if (this.data.record_locked) {
            // Frozen with the record's layer.
            return details;
        }
        if (request.is_own) {
            if (request.request_state === "closed") {
                actions.append(
                    button("btn-link p-0", _t("Reopen"), () =>
                        this.setRequestState(request, "open")
                    )
                );
            } else {
                actions.append(
                    button("btn-link p-0", _t("Close"), () =>
                        this.setRequestState(request, "closed")
                    )
                );
            }
        } else if (request.request_state !== "closed") {
            actions.append(
                button("btn-link p-0", _t("Respond"), () =>
                    this.editResponse(request, details)
                )
            );
        }
        return details;
    },

    editResponse(request, details) {
        const textarea = htmlElement("textarea", "form-control form-control-sm mt-1");
        textarea.rows = 2;
        textarea.value = request.response || "";
        textarea.placeholder = _t("Fixed in the next revision, or why not...");
        const actions = htmlElement("div", "o_agx_annotation_popover_actions");
        actions.append(
            button("btn-primary", _t("Save"), async () => {
                const saved = await this.call(
                    "annotation_respond",
                    request.id,
                    textarea.value
                );
                this.applyRequest(saved);
            }),
            button("btn-secondary", _t("Cancel"), () =>
                details.replaceWith(this.requestDetails(request))
            )
        );
        details.querySelector(".o_agx_annotation_popover_actions")?.remove();
        details.append(textarea, actions);
        textarea.focus();
    },

    async setRequestState(request, state) {
        const saved = await this.call(
            "annotation_set_request_state",
            request.id,
            state
        );
        this.applyRequest(saved);
    },

    /**
     * Take in a Change request the server returned after a change.
     */
    applyRequest(saved) {
        const annotation = this.annotations.find((a) => a.id === saved.id);
        if (annotation) {
            Object.assign(annotation, saved);
        }
        const requests = this.data.requests || [];
        const index = requests.findIndex((request) => request.id === saved.id);
        if (index >= 0) {
            requests[index] = {...requests[index], ...saved};
        } else {
            requests.push(saved);
        }
        this.closePopover();
        this.redraw();
        this.renderRequests();
    },

    toggleRequests() {
        this.requestsOpen = !this.requestsOpen;
        this.renderRequests();
    },

    /**
     * Panel of the Change requests not closed on any revision of the file.
     */
    renderRequests() {
        const requests = [...(this.data.requests || [])].sort(
            (a, b) =>
                a.revision_number - b.revision_number || a.page - b.page || a.id - b.id
        );
        const waiting = requests.filter((r) => r.request_state !== "closed").length;
        this.requestsButton.innerHTML = '<i class="fa fa-exclamation-circle"></i>';
        if (waiting) {
            this.requestsButton.append(htmlElement("span", "ms-1", String(waiting)));
        }
        this.requestsButton.classList.toggle("active", this.requestsOpen);
        this.requestsPanel.classList.toggle("d-none", !this.requestsOpen);
        const items = requests.map((request) => {
            const item = htmlElement("div", "o_agx_annotation_requests_item");
            item.classList.toggle(
                "o_agx_annotation_requests_elsewhere",
                request.attachment_id !== this.attachment.id
            );
            item.append(
                htmlElement(
                    "div",
                    "o_agx_annotation_popover_meta",
                    sprintf(
                        _t("Revision %s · page %s · %s"),
                        request.revision_number,
                        request.page,
                        request.author_name
                    )
                ),
                htmlElement("div", "o_agx_annotation_popover_text", request.text),
                this.requestDetails(request)
            );
            item.querySelector(".o_agx_annotation_popover_actions")?.prepend(
                button("btn-link p-0", _t("Show"), () => this.showRequest(request))
            );
            return item;
        });
        this.requestsPanel.replaceChildren(
            htmlElement(
                "div",
                "o_agx_annotation_requests_title",
                _t("Change requests")
            ),
            ...items
        );
        if (!items.length) {
            this.requestsPanel.append(
                htmlElement(
                    "div",
                    "o_agx_annotation_requests_empty",
                    _t("No open change requests.")
                )
            );
        }
    },

    async showRequest(request) {
        if (request.attachment_id !== this.attachment.id) {
            await this.showRevision(request.attachment_id);
        }
        this.focusAnnotation(request.id);
    },

    /**
     * Scroll to the pin of the annotation `id` and open it.
     */
    focusAnnotation(id) {
        const annotation = this.annotations.find((a) => a.id === id);
        const sheet =
            annotation && this.sheets.find((s) => s.number === annotation.page);
        if (!sheet) {
            return;
        }
        const top =
            sheet.element.getBoundingClientRect().top -
            this.scroll.getBoundingClientRect().top +
            annotation.geometry.y * sheet.element.clientHeight;
        this.scroll.scrollTop += top - this.scroll.clientHeight / 3;
        this.openComment(sheet, annotation);
    },

    // ------------------------------------------------------------ revisions

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
                `/agx_photoviewer_annotation_review/revise/${this.attachment.id}`,
                {method: "POST", body}
            );
            const result = await response.json();
            if (result.error) {
                this.showError(result.error);
                return;
            }
            await this.switchAttachment(result);
        } finally {
            if (this.reviseButton) {
                this.reviseButton.disabled = false;
            }
        }
    },

    showError(message) {
        this.root.querySelector(".o_agx_annotation_error")?.remove();
        this.body.before(
            htmlElement(
                "div",
                "o_agx_annotation_error alert alert-danger m-0 py-1 px-2",
                message
            )
        );
    },
});
