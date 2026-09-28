/** @odoo-module **/

import {patch} from "@web/core/utils/patch";
import {AnalyticDistribution} from "@analytic/components/analytic_distribution/analytic_distribution";
import {AnalyticTreeDialog} from "../components/analytic_tree_dialog";

patch(AnalyticDistribution.prototype, "account_analytic_distribution_ztree", {
    planHasZtree(groupId) {
        const plan = this.allPlans.find((p) => p.id === groupId);
        return !!(plan && plan.use_ztree_widget);
    },

    async loadOptionsSourceAnalytic(groupId, searchTerm) {
        const options = await this._super(groupId, searchTerm);
        if (!searchTerm && this.planHasZtree(groupId)) {
            options.unshift({
                label: this.env._t("Browse tree…"),
                classList: "o_m2o_dropdown_option",
                action: (editedTag) => this.onBrowseAnalyticTree(groupId, editedTag),
            });
        }
        return options;
    },

    // Mirrors _onSearchMore: keep the popup open (selectCreateIsOpen) while
    // the dialog is up, and refocus the name cell if nothing got picked.
    onBrowseAnalyticTree(groupId, editedTag) {
        this.selectCreateIsOpen = true;
        this.addDialog(
            AnalyticTreeDialog,
            {
                title: this.env._t("Select Analytic Account"),
                domain: this.analyticAccountDomain(groupId),
                onSelected: (id, displayName) => {
                    editedTag.analytic_account_id = id;
                    editedTag.analytic_account_name = displayName;
                    this.setFocusSelector(
                        `.tag_${editedTag.id} .o_analytic_percentage`
                    );
                    this.autoFill();
                },
            },
            {
                onClose: () => {
                    this.selectCreateIsOpen = false;
                    if (!editedTag.analytic_account_id) {
                        this.setFocusSelector(
                            `.tag_${editedTag.id} .o_analytic_account_name`
                        );
                        this.focusToSelector();
                    }
                },
            }
        );
    },
});
