/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Many2XAutocomplete } from "@web/views/fields/relational_utils";
import { Many2OneField } from "@web/views/fields/many2one/many2one_field";

// The stock Many2one dropdown shows a single truncated line per option — for a
// contact that is rarely enough to tell people and companies apart while
// typing. This widget swaps in a rich, multi-line option template (name, type,
// VAT, address, e-mail, phone), enriched by one batched
// res.partner.get_partner_autocomplete_info call per set of options shown.
// Registered for both form and list so the same widget="partner_autocomplete"
// renders the rich dropdown in a normal field and inside a tree cell.

class PartnerM2XAutocomplete extends Many2XAutocomplete {
    // this.orm is already provided by the base Many2XAutocomplete.setup().

    get optionsSource() {
        return {
            ...super.optionsSource,
            optionTemplate: "agx_partner_autocomplete.Option",
        };
    }

    async loadOptionsSource(request) {
        const options = await super.loadOptionsSource(request);
        // Only enrich when the field actually points at res.partner; applied to
        // any other comodel the widget degrades to the plain dropdown.
        if (this.props.resModel !== "res.partner") {
            return options;
        }
        // Action rows (Create…, Search More…, Start typing…) have no `value` —
        // leave them to fall back to their plain label.
        const ids = options.filter((o) => o.value).map((o) => o.value);
        if (ids.length) {
            const infos = await this.orm.call(
                "res.partner",
                "get_partner_autocomplete_info",
                [ids]
            );
            const byId = Object.fromEntries(infos.map((i) => [i.id, i]));
            for (const o of options) {
                const info = o.value && byId[o.value];
                if (info) {
                    o.partnerInfo = info;
                    // Applied to the <li>; the scss uses it to undo the
                    // single-line clamp the dropdown puts on every item.
                    o.classList = "o_partner_ac_item";
                }
            }
        }
        return options;
    }
}

export class PartnerAutocompleteM2oField extends Many2OneField {}
PartnerAutocompleteM2oField.components = {
    ...Many2OneField.components,
    Many2XAutocomplete: PartnerM2XAutocomplete,
};

registry.category("fields").add("partner_autocomplete", PartnerAutocompleteM2oField);
// Register the list variant too so the rich dropdown works in editable trees;
// mirrors how core pins many2one for list to avoid the legacy fallback.
registry
    .category("fields")
    .add("list.partner_autocomplete", PartnerAutocompleteM2oField);
