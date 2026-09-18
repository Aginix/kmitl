/** @odoo-module */

import { useBus, useService } from "@web/core/utils/hooks";
import { formatMonetary } from "@web/views/fields/formatters";

const { Component, onWillStart, useState } = owl;

export class ReceiptDashboard extends Component {
    setup() {
        super.setup();
        this.orm = useService("orm");
        this.state = useState({ data: {} });

        onWillStart(() => this._reload());

        if (this.env.searchModel) {
            useBus(this.env.searchModel, "update", () => this._reload());
        }
    }

    async _reload() {
        const domain = this.env.searchModel
            ? this.env.searchModel.domain
            : [];
        this.state.data = await this.orm.call(
            "kmitl.receipt",
            "get_receipt_dashboard",
            [domain]
        );
    }

    renderMonetaryField(value, currencyId) {
        return formatMonetary(value, { currencyId });
    }
}
ReceiptDashboard.template = "receipt_kmitl.ReceiptDashboard";
