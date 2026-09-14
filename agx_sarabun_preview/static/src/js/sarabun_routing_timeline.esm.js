/** @odoo-module **/

import { registry } from "@web/core/registry";
import { standardWidgetProps } from "@web/views/widgets/standard_widget_props";
import { useService } from "@web/core/utils/hooks";
import { Dialog } from "@web/core/dialog/dialog";

const { Component, useState } = owl;

const COLLAPSE_STORAGE_KEY = "sarabun.timeline.collapsed";

/**
 * Vertical routing-timeline visual for sarabun.document. Renders the current
 * attempt's Route (or an archived attempt) as a top-to-bottom sequence of
 * Stage rows; parallel steps within a Stage sit side-by-side; step cards are
 * colored by state/disposition. Read-only — no click-to-open, no acting here.
 *
 * Two adapters register this component into the framework:
 *   - SarabunRoutingTimelineWidget: a view widget used as
 *     <widget name="sarabun_routing_timeline"/> inside a form or wizard; reads
 *     its data from the record's routing_preview_json field.
 *   - SarabunRoutingTimelineDialog: a client action tag
 *     "sarabun_routing_timeline_archive" that opens a dialog listing every
 *     archived attempt as its own timeline.
 */
export class SarabunRoutingTimeline extends Component {
    stepClass(step) {
        const classes = ["o_sarabun_step"];
        if (step.state === "waiting") classes.push("o_sarabun_step--waiting");
        else if (step.state === "active") classes.push("o_sarabun_step--active");
        else if (step.state === "skipped") classes.push("o_sarabun_step--skipped");
        else if (step.state === "done") {
            const d = step.disposition;
            if (d === "return") classes.push("o_sarabun_step--done-return");
            else if (d === "reject") classes.push("o_sarabun_step--done-reject");
            else if (d === "delegate") classes.push("o_sarabun_step--done-delegate");
            else classes.push("o_sarabun_step--done-complete");
        }
        if (step.is_originator) classes.push("o_sarabun_step--originator");
        if (step.for_info) classes.push("o_sarabun_step--cc");
        return classes.join(" ");
    }

    stateLabel(step) {
        if (step.state === "active") return "🎯 อยู่ที่นี่";
        if (step.state === "waiting") return "รอ";
        if (step.state === "skipped") return "ข้าม";
        const d = step.disposition;
        if (d === "return") return "↩ ตีกลับ";
        if (d === "reject") return "✗ ปฏิเสธ";
        if (d === "delegate") return "↪ มอบหมาย";
        if (d === "direct") return "✓ เกษียนสั่งการ";
        return "✓ ผ่านแล้ว";
    }
}
SarabunRoutingTimeline.template = "agx_sarabun_preview.SarabunRoutingTimeline";
SarabunRoutingTimeline.props = {
    data: { type: Object, optional: true },
    open: { type: Boolean, optional: true },
    showToggle: { type: Boolean, optional: true },
    onToggle: { type: Function, optional: true },
    onOpenHistory: { type: Function, optional: true },
};
SarabunRoutingTimeline.defaultProps = {
    open: true,
    showToggle: false,
};

/**
 * View-widget adapter: parses routing_preview_json off the record, owns the
 * collapse toggle state (per-user sticky via localStorage on the form; always
 * open on the wizard because the widget has no resId on transient records).
 */
export class SarabunRoutingTimelineWidget extends Component {
    setup() {
        this.action = useService("action");
        this.orm = useService("orm");
        // Default: open on wizards (transient — no resId persists), collapsed on
        // regular form records (persisted via localStorage).
        const isForm = !!this.props.record.resId;
        const stored = isForm ? this._readStoredCollapsed() : null;
        this.state = useState({ open: stored === null ? !isForm : !stored });
    }

    _readStoredCollapsed() {
        try {
            const raw = window.localStorage.getItem(COLLAPSE_STORAGE_KEY);
            return raw === null ? null : raw === "1";
        } catch (e) {
            return null;
        }
    }

    _writeStoredCollapsed(collapsed) {
        try {
            window.localStorage.setItem(COLLAPSE_STORAGE_KEY, collapsed ? "1" : "0");
        } catch (e) {
            // localStorage unavailable (private mode) — silently ignore.
        }
    }

    get payload() {
        const raw = this.props.record.data.routing_preview_json;
        if (!raw) return { attempt_seq: 1, has_history: false, stages: [] };
        try {
            return JSON.parse(raw);
        } catch (e) {
            return { attempt_seq: 1, has_history: false, stages: [] };
        }
    }

    toggle() {
        this.state.open = !this.state.open;
        if (this.props.record.resId) {
            this._writeStoredCollapsed(!this.state.open);
        }
    }

    async openHistory() {
        const docId = this.props.record.resId
            || (this.props.record.data.document_id && this.props.record.data.document_id[0]);
        if (!docId) return;
        const action = await this.orm.call(
            "sarabun.document",
            "action_open_routing_history",
            [[docId]],
        );
        await this.action.doAction(action);
    }
}
SarabunRoutingTimelineWidget.template = "agx_sarabun_preview.SarabunRoutingTimelineWidget";
SarabunRoutingTimelineWidget.components = { SarabunRoutingTimeline };
SarabunRoutingTimelineWidget.props = { ...standardWidgetProps };

registry
    .category("view_widgets")
    .add("sarabun_routing_timeline", SarabunRoutingTimelineWidget);

/**
 * Client action tag "sarabun_routing_timeline_archive": opens a dialog listing
 * every archived attempt as its own timeline. Data arrives pre-rendered in
 * action.params.attempts so no extra RPC fires when the modal opens.
 */
export class SarabunRoutingTimelineDialog extends Component {
    setup() {
        const params = (this.props.action && this.props.action.params) || {};
        this.attempts = params.attempts || [];
    }
}
SarabunRoutingTimelineDialog.template = "agx_sarabun_preview.SarabunRoutingTimelineDialog";
SarabunRoutingTimelineDialog.components = { Dialog, SarabunRoutingTimeline };
SarabunRoutingTimelineDialog.props = ["*"];

registry
    .category("actions")
    .add("sarabun_routing_timeline_archive", SarabunRoutingTimelineDialog);
