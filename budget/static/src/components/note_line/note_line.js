/** @odoo-module **/

import { registry } from "@web/core/registry";
import { ListRenderer } from "@web/views/list/list_renderer";
import { X2ManyField } from "@web/views/fields/x2many/x2many_field";

export class NoteLineRenderer extends ListRenderer {
    setup() {
      super.setup();
    }
  }
  NoteLineRenderer.template = "budget.NoteLineRenderer";
  NoteLineRenderer.recordRowTemplate = "budget.ListRenderer.RecordRow";

export class NoteLine extends X2ManyField {
    setup() {
        super.setup();
    }
}
NoteLine.components = {
    ...X2ManyField.components,
    ListRenderer: NoteLineRenderer,
}

registry.category("fields").add("budget_line", NoteLine);
