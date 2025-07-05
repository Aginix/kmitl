/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Many2OneField } from "@web/views/fields/many2one/many2one_field"

export class HelperField extends Many2OneField {
    setup() {
        super.setup()
    }
}

HelperField.template = "budget.Helper_field"
HelperField.supportedTypes = ['many2one']

registry.category("fields").add("helper_field", HelperField);
