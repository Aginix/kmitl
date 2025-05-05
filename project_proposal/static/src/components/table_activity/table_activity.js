/** @odoo-module **/

import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { X2ManyField } from "@web/views/fields/x2many/x2many_field";
import { List_rendererer_activity } from "../list_renderer_activity/list_renderer_activity"

export class Table_activity extends X2ManyField {
  setup() {
    super.setup();
    
  }
}

Table_activity.props = {
  ...standardFieldProps,
  addLabel: { type: String, optional: true },
  editable: { type: String, optional: true },
};
Table_activity.template = "project_proposal.Table_activity";
Table_activity.components = {
  List_rendererer_activity,
};

registry.category("fields").add("table_activity", Table_activity);
