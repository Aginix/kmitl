/** @odoo-module **/

import { ListRenderer } from "@web/views/list/list_renderer";
import {
  useState,

} from "@odoo/owl";

export class List_rendererer_activity extends ListRenderer {
  setup() {
    super.setup();
    const total = this.props.list.records.reduce((sum, rec) => sum + rec.data.amount, 0);

  }
  freezeColumnWidths() {}

  test(data) {
    console.log(data);
  }
}

List_rendererer_activity.template = "project_proposal.List_renderer_activity";

List_rendererer_activity.rowsTemplate = "renderer_activity.ListRenderer.Rows";
List_rendererer_activity.recordRowTemplate =
  "renderer_activity.ListRenderer.RecordRow";

List_rendererer_activity.props = [
  "activeActions?",
  "list",
  "archInfo",
  "openRecord",
  "onAdd?",
  "cycleOnTab?",
  "allowSelectors?",
  "editable?",
  "noContentHelp?",
  "nestedKeyOptionalFieldsData?",
  "readonly?",
  "onOptionalFieldsChanged?",
];
