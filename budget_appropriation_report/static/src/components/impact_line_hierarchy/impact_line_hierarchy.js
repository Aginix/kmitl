/** @odoo-module **/

import { Component, useState, onWillStart, onWillUpdateProps } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";
import { standardWidgetProps } from "@web/views/widgets/standard_widget_props";

export class ImpactLineHierarchy extends Component {
    setup() {
        this.orm = useService("orm");
        this.state = useState({
            hierarchy: [],
            totalAmount: 0,
            loading: true,
        });

        onWillStart(() => this.loadHierarchy());
        onWillUpdateProps(() => this.loadHierarchy());
    }

    get impactType() {
        return this.props.impactType || null;
    }

    async loadHierarchy() {
        const reportId = this.props.record.resId;
        const impactType = this.impactType;

        if (!reportId) {
            this.state.hierarchy = [];
            this.state.totalAmount = 0;
            this.state.loading = false;
            return;
        }

        try {
            const result = await this.orm.call(
                "budget.appropriation.report",
                "get_impact_line_hierarchy",
                [reportId, impactType]
            );

            this.state.hierarchy = result.hierarchy || [];
            this.state.totalAmount = result.total_amount || 0;
        } catch (error) {
            console.error("Error loading impact line hierarchy:", error);
            this.state.hierarchy = [];
            this.state.totalAmount = 0;
        } finally {
            this.state.loading = false;
        }
    }

    formatCurrency(amount) {
        return new Intl.NumberFormat('th-TH', {
            minimumFractionDigits: 0,
            maximumFractionDigits: 0
        }).format(amount || 0);
    }
}

ImpactLineHierarchy.template = "budget_appropriation_report.ImpactLineHierarchy";
ImpactLineHierarchy.props = {
    ...standardWidgetProps,
    impactType: { type: String, optional: true },
    title: { type: String, optional: true },
};
ImpactLineHierarchy.extractProps = ({ attrs }) => {
    return {
        impactType: attrs.impact_type,
        title: attrs.title,
    };
};

registry.category("view_widgets").add("budget_appropriation_impact_hierarchy", ImpactLineHierarchy);
