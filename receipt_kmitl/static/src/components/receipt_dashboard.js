/** @odoo-module */

import { useService } from "@web/core/utils/hooks";
import { formatMonetary } from "@web/views/fields/formatters";

const { Component, onWillStart, useState } = owl;

export class ReceiptDashboard extends Component {
    setup() {
        super.setup();
        this.orm = useService("orm");
        this.state = useState({ data: {} });

        onWillStart(async () => {
            this.state.data = await this.orm.call(
                "kmitl.receipt",
                "get_receipt_dashboard",
                []
            );
        });
    }

    renderMonetaryField(value, currencyId) {
        return formatMonetary(value, { currencyId });
    }
}
ReceiptDashboard.template = "receipt_kmitl.ReceiptDashboard";
