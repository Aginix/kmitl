/** @odoo-module **/

import {X2ManyField} from "@web/views/fields/x2many/x2many_field";
import {registry} from "@web/core/registry";

/**
 * A one2many/many2many field that does NOT open a record dialog when the field
 * is readonly — clicking a row in a read-only table should do nothing (Odoo's
 * default opens a read-only form dialog on row click). Editable behaviour is
 * unchanged. Used on the plan/participant/actual tables so a locked request
 * can't be poked open.
 */
export class NoOpenReadonlyX2Many extends X2ManyField {
    async openRecord(record) {
        if (this.props.readonly) {
            return;
        }
        return super.openRecord(record);
    }
}
registry.category("fields").add("no_open_readonly_x2many", NoOpenReadonlyX2Many);
