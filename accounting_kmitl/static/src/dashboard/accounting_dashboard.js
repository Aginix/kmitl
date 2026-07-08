/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { Component, onWillStart, useState } from "@odoo/owl";

// Landing "work launchpad" for the Accounting app: a grid of KPI cards that
// each open a filtered list, plus quick-create buttons. The cards (labels,
// colours, domains and counts) are fully defined by the
// accounting.kmitl.dashboard server model, so other modules can add cards
// without touching this component.
export class AccountingDashboard extends Component {
    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.state = useState({
            loading: true,
            data: { currency_symbol: "", cards: [] },
        });

        onWillStart(async () => {
            this.state.data = await this.orm.call(
                "accounting.kmitl.dashboard",
                "get_dashboard_data",
                []
            );
            this.state.loading = false;
        });
    }

    // Cards as delivered by the server, in display order.
    get cards() {
        return [...(this.state.data.cards || [])].sort(
            (a, b) => a.sequence - b.sequence
        );
    }

    get text() {
        return {
            title: _t("Accounting Dashboard"),
            subtitle: _t("Overview of pending work and outstanding balances"),
            quickActions: _t("Quick actions"),
            newVendorBill: _t("New vendor bill"),
            newCustomerInvoice: _t("New customer invoice"),
            newJournalEntry: _t("New journal entry"),
        };
    }

    formatAmount(value) {
        return (value || 0).toLocaleString("th-TH", {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2,
        });
    }

    // Open the card's model filtered to exactly its domain, so the list
    // contents match the number shown on the card.
    openCard(card) {
        if (!card.domain) {
            return;
        }
        this.action.doAction({
            type: "ir.actions.act_window",
            name: card.title,
            res_model: card.res_model,
            domain: card.domain,
            views: [
                [false, "list"],
                [false, "form"],
            ],
            target: "current",
        });
    }

    // Quick-create: open a blank account.move form of the requested type.
    newDoc(moveType) {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "account.move",
            views: [[false, "form"]],
            target: "current",
            context: { default_move_type: moveType },
        });
    }
}

AccountingDashboard.template = "accounting_kmitl.AccountingDashboard";

registry.category("actions").add("accounting_kmitl.dashboard", AccountingDashboard);
