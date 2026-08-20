/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Many2XAutocomplete } from "@web/views/fields/relational_utils";
import { BudgetCommitmentInfoField } from "@budget/commitment_info/budget_commitment_info";

// The stock Many2one dropdown shows one line of plain text per option — not
// enough to tell reservations apart by code / dimensions / leftover while
// searching. This swaps in a rich optionTemplate for the dropdown itself,
// batch-enriched by the same get_reservation_info() payload the selected-value
// card (BudgetCommitmentInfoField) already uses.
class BudgetCommitmentM2XAutocomplete extends Many2XAutocomplete {
    setup() {
        super.setup();
        this.orm = useService("orm");
    }

    get optionsSource() {
        return { ...super.optionsSource, optionTemplate: "budget_commitment_m2o.Option" };
    }

    async loadOptionsSource(request) {
        const options = await super.loadOptionsSource(request);
        // Action rows (Create…, Search More…) have no `value` id — leave those
        // untouched so the template falls back to their plain label.
        const ids = options.filter((o) => o.value).map((o) => o.value);
        if (ids.length) {
            const infos = await this.orm.call("budget.commitment", "get_reservation_info", [
                ids,
            ]);
            const byId = Object.fromEntries(infos.map((i) => [i.id, i]));
            for (const o of options) {
                const info = o.value && byId[o.value];
                if (info) {
                    o.commitmentInfo = info;
                    // Applied to the <li> — the scss uses it to undo the
                    // <a class="text-truncate"> single-line clamp.
                    o.classList = "o_bcm2o_item";
                }
            }
        }
        return options;
    }
}

export class BudgetCommitmentM2oField extends BudgetCommitmentInfoField {}
BudgetCommitmentM2oField.components = {
    ...BudgetCommitmentInfoField.components,
    Many2XAutocomplete: BudgetCommitmentM2XAutocomplete,
};

// Replaces the "budget_commitment_info" entry rather than registering under a
// new name: every existing/future `widget="budget_commitment_info"` field
// gets the rich dropdown for free the moment this module is installed, with
// no view changes anywhere. Safe because this class is a strict superset of
// BudgetCommitmentInfoField (same info card, adds only the dropdown).
registry.category("fields").add("budget_commitment_info", BudgetCommitmentM2oField, {
    force: true,
});
