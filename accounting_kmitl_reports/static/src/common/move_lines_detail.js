/** @odoo-module **/

import { Component } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";

/**
 * Shared expand-detail panel for every KMITL report whose rows expand to the
 * underlying journal entry (General Ledger, General Journal). Rendering the
 * same component everywhere keeps the detail format identical.
 *
 * Props:
 *  - lines: Array<{id, account, label, partner, debit, credit, dimensions}>
 *           (from the report model's get_move_lines_detail RPC)
 *  - narration / maker / makerDate: entry-level metadata (strings)
 *  - onOpen: optional callback to open the source journal entry
 */
export class MoveLinesDetail extends Component {
    setup() {
        this.labels = {
            account: _t("Account"),
            label: _t("Label"),
            partner: _t("Partner"),
            debit: _t("Debit"),
            credit: _t("Credit"),
            narration: _t("Narration"),
            maker: _t("Maker"),
            open: _t("Open"),
        };
    }

    // The entry's accounting dimensions, shown once in the panel header:
    // the distinct dimensions across all of the entry's lines.
    get headerDims() {
        const seen = new Set();
        const out = [];
        for (const ml of this.props.lines || []) {
            for (const dim of ml.dimensions || []) {
                const key = `${dim.label}|${dim.value}`;
                if (!seen.has(key)) {
                    seen.add(key);
                    out.push(dim);
                }
            }
        }
        return out;
    }

    format(value) {
        if (!value || Math.abs(value) < 0.005) {
            return "";
        }
        return value.toLocaleString(undefined, {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2,
        });
    }
}

MoveLinesDetail.template = "accounting_kmitl_reports.MoveLinesDetail";
MoveLinesDetail.props = {
    lines: { type: Array, optional: true },
    narration: { type: String, optional: true },
    maker: { type: String, optional: true },
    makerDate: { type: String, optional: true },
    onOpen: { type: Function, optional: true },
};
MoveLinesDetail.defaultProps = {
    lines: [],
    narration: "",
    maker: "",
    makerDate: "",
    onOpen: false,
};
