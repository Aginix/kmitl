/** @odoo-module **/

import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { Component, onMounted, onWillUnmount, useState } from "@odoo/owl";

function formatElapsed(ms) {
    if (ms < 0) {
        ms = 0;
    }
    const totalSeconds = Math.floor(ms / 1000);
    const days = Math.floor(totalSeconds / 86400);
    const hours = Math.floor((totalSeconds % 86400) / 3600);
    const minutes = Math.floor((totalSeconds % 3600) / 60);
    const seconds = totalSeconds % 60;

    if (days > 0) {
        return `${days}d ${hours}h`;
    }
    if (hours > 0) {
        return `${hours}h ${minutes}m`;
    }
    if (minutes > 0) {
        return `${minutes}m ${seconds}s`;
    }
    return `${seconds}s`;
}

export class StateLeadtimeLive extends Component {
    setup() {
        this.state = useState({ display: this._compute() });
        this._interval = null;

        onMounted(() => {
            this._interval = window.setInterval(() => {
                this.state.display = this._compute();
            }, 1000);
        });

        onWillUnmount(() => {
            if (this._interval !== null) {
                window.clearInterval(this._interval);
                this._interval = null;
            }
        });
    }

    _compute() {
        const value = this.props.value;
        if (!value) {
            return "—";
        }
        const entryMs = value.ts;
        if (!entryMs) {
            return "—";
        }
        return formatElapsed(Date.now() - entryMs);
    }
}

StateLeadtimeLive.template = "base_state_leadtime.StateLeadtimeLive";
StateLeadtimeLive.props = { ...standardFieldProps };
StateLeadtimeLive.supportedTypes = ["datetime"];

registry.category("fields").add("state_leadtime_live", StateLeadtimeLive);
