/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Many2XAutocomplete } from "@web/views/fields/relational_utils";
import { Many2OneField } from "@web/views/fields/many2one/many2one_field";

// The stock Many2one dropdown gives no hint whether a route template is
// personal, unit-shared, or public — a private and a public one look identical
// while picking. This widget swaps in a small option template that prints the
// name plus a coloured visibility badge, enriched by one batched read() per set
// of options shown.

const VISIBILITY_LABEL = {
    personal: "ส่วนตัว",
    unit: "สังกัด",
    public: "ทุกคน",
};

const VISIBILITY_BADGE_CLASS = {
    personal: "text-bg-secondary",
    unit: "text-bg-info",
    public: "text-bg-success",
};

class RouteTemplateM2XAutocomplete extends Many2XAutocomplete {
    setup() {
        super.setup();
        this.orm = useService("orm");
    }

    get optionsSource() {
        return {
            ...super.optionsSource,
            optionTemplate: "agx_sarabun_route_template_widget.Option",
        };
    }

    async loadOptionsSource(request) {
        const options = await super.loadOptionsSource(request);
        // Action rows (Create…, Search More…, Start typing…) carry no `value` —
        // leave those to fall back to their plain label.
        const ids = options.filter((o) => o.value).map((o) => o.value);
        if (ids.length) {
            const records = await this.orm.read(
                "sarabun.route.template",
                ids,
                ["visibility"]
            );
            const byId = Object.fromEntries(records.map((r) => [r.id, r]));
            for (const o of options) {
                const rec = o.value && byId[o.value];
                if (rec && rec.visibility) {
                    o.visibility = rec.visibility;
                    o.visibilityLabel = VISIBILITY_LABEL[rec.visibility] || rec.visibility;
                    o.visibilityClass =
                        VISIBILITY_BADGE_CLASS[rec.visibility] || "text-bg-secondary";
                    // Applied to the <li>; the scss uses it to undo the
                    // single-line clamp the dropdown puts on every item.
                    o.classList = "o_sarabun_route_tpl_item";
                }
            }
        }
        return options;
    }
}

export class RouteTemplateM2oField extends Many2OneField {}
RouteTemplateM2oField.components = {
    ...Many2OneField.components,
    Many2XAutocomplete: RouteTemplateM2XAutocomplete,
};

registry
    .category("fields")
    .add("sarabun_route_template_m2o", RouteTemplateM2oField);
// Register the list variant too so the badge dropdown works in editable trees;
// mirrors how core pins many2one for list to avoid the legacy fallback.
registry
    .category("fields")
    .add("list.sarabun_route_template_m2o", RouteTemplateM2oField);
