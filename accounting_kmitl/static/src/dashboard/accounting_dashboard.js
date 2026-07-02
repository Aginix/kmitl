/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { Component, onWillStart, useState } from "@odoo/owl";

// Landing "work launchpad" for the Accounting app: a grid of KPI cards that
// each open a filtered account.move list, plus quick-create buttons. All the
// figures (and the domain behind every card) come from the
// accounting.kmitl.dashboard server model.
export class AccountingDashboard extends Component {
    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.state = useState({
            loading: true,
            data: { currency_symbol: "", cards: {} },
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

    // Card display metadata (render order + labels + accent colour). The values
    // themselves are matched by id from the server payload.
    get cardDefs() {
        return [
            { id: "my_drafts", title: _t("My draft documents"), color: "secondary" },
            {
                id: "submitted",
                title: _t("Submitted (awaiting posting)"),
                color: "info",
            },
            {
                id: "unpaid_ap",
                title: _t("Unpaid vendor bills"),
                color: "warning",
                money: true,
            },
            {
                id: "overdue_ap",
                title: _t("Overdue vendor bills"),
                color: "danger",
                money: true,
            },
            {
                id: "unpaid_ar",
                title: _t("Unpaid customer invoices"),
                color: "primary",
                money: true,
            },
            {
                id: "exceptions",
                title: _t("Documents with exceptions"),
                color: "danger",
            },
        ];
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

    cardValue(def) {
        return this.state.data.cards[def.id] || { count: 0, amount: 0 };
    }

    formatAmount(value) {
        return (value || 0).toLocaleString("th-TH", {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2,
        });
    }

    // Open the account.move list filtered to exactly the card's domain, so the
    // list contents match the number shown on the card.
    openCard(def) {
        const card = this.cardValue(def);
        if (!card.domain) {
            return;
        }
        this.action.doAction({
            type: "ir.actions.act_window",
            name: def.title,
            res_model: "account.move",
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
