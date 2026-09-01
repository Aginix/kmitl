/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Many2OneField } from "@web/views/fields/many2one/many2one_field";
import { onWillStart, onWillUpdateProps, useState } from "@odoo/owl";

// A reservation is picked by *what it is for*, but a Many2one shows one line of
// text — so a user choosing a ใบจองงบประมาณ to draw down could not tell whether
// the code, the dimensions or the leftover matched their document. This widget
// keeps the standard Many2one picker and renders the selected reservation's
// details underneath it: budget code, all four financial dimensions, fiscal year
// and the amounts (วงเงินอนุมัติ / ผูกพันแล้ว / คงเหลือให้ผูกพัน).
//
// Everything displayed comes from budget.commitment.get_reservation_info() as
// label/value rows, so labels, translations and money formatting live
// server-side and bridge modules (e.g. budget_operating_unit, which appends the
// owning/beneficiary unit) enrich the panel without touching this file.
export class BudgetCommitmentInfoField extends Many2OneField {
    setup() {
        super.setup();
        this.orm = useService("orm");
        this.info = useState({ data: null });
        onWillStart(() => this.loadInfo(this.commitmentId(this.props)));
        onWillUpdateProps((nextProps) => this.loadInfo(this.commitmentId(nextProps)));
    }

    commitmentId(props) {
        return (props.value && props.value[0]) || false;
    }

    async loadInfo(commitmentId) {
        // The card is a form-only affordance: in a list/tree view it would
        // render a full card in every cell of every row.
        if (!commitmentId || this.env.config.viewType === "list") {
            this.info.data = null;
            return;
        }
        if (this.info.data && this.info.data.id === commitmentId) {
            return;
        }
        const [data] = await this.orm.call(
            "budget.commitment",
            "get_reservation_info",
            [[commitmentId]]
        );
        this.info.data = data || null;
    }
}

BudgetCommitmentInfoField.template = "budget.BudgetCommitmentInfoField";

registry.category("fields").add("budget_commitment_info", BudgetCommitmentInfoField);
