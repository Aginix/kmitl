# Web Widget X2many Flow Diagram

Generic web widget that shows a one2many as a diagram of layered cards instead of a
table. It is purely presentational: it knows nothing about what the lines mean, only how
they are ordered.

## Language

**Flow Diagram (แผนภาพลำดับ)**: A one2many drawn as Layers of Nodes, top-to-bottom or
left-to-right. _Avoid_: graph, workflow (there are no edges between individual lines and
no execution semantics).

**Layer (ชั้น)**: The lines that share one Layer Key value, drawn side by side. Layers
are numbered "ชั้น 1, 2, …" by position, not by their raw value. A consumer may give a
Layer business meaning (e-Saraban's **Stage** is one Layer), but the widget does not.
_Avoid_: stage (e-Saraban's term), level, step.

**Layer Key**: The numeric field (Integer or Float) whose value puts a line in its
Layer. _Avoid_: sequence (only one possible field name).

**Node (โหนด)**: The card of one line.

**Locked Node**: A Node whose Layer Key is readonly for that line; it can neither be
moved nor be pushed by another move, and cannot be removed from its card.

**Anchored Layer**: A first Layer holding a Locked Node (e-Saraban's originator):
nothing may join it, be added to it or be placed before it, so it stays first and alone.

**Join**: Dropping a Node onto an existing Layer — it takes that Layer's value.

**New Layer**: Dropping a Node between Layers (or before the first / after the last) —
it gets a Layer of its own.

**Minimal Shift**: The renumbering rule of a New Layer: take a free value in the gap if
there is one, otherwise move only the Layers after the gap up by one. Gaps in the
numbering are normal and never compacted (ADR-0001).
