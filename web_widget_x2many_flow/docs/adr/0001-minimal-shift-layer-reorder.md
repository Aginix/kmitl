# Minimal Shift instead of consecutive renumbering

Dragging a Node between Layers must produce a New Layer without disturbing the rest.
Odoo's own drag-and-drop (`StaticList.resequence`, used by `widget="handle"`) rewrites
the moved range as consecutive integers `offset + i`: it gives every line its own value,
so any Layer of two or more lines would be split apart by a single drag. We therefore
compute the Layer Key writes ourselves (`planDrop`) and apply them in one
`StaticList.applyCommands` call.

The rule: a free value in the gap is used as is; otherwise only the Layers **after** the
gap move up by one. Before the first Layer is `first - 1`, after the last is `last + 1`.
Earlier Layers are never written.

A drop is refused when it would push a Locked Node. A first Layer holding a Locked Node
is an **Anchored Layer**: nothing may join it, be added to it ("+" is hidden) or be
placed before it. Nothing is written to it in those cases, but e-Saraban's originator
must stay first and alone — a gating step that joined it would be passed the moment the
originator auto-signs at send, without anyone acting on it.

## Considered options

- **Odoo `resequence`** — rejected: destroys Layers (see above).
- **Dense renumber `1..N` after every drop** — tidy numbers, but writes every line,
  including Locked ones; e-Saraban's originator step rejects any `order` write
  (`sarabun.routing.step.write`), so saving would fail.
- **Minimal Shift** — chosen: writes the fewest lines, and a drop that would push a
  Locked Node can be refused up front with a clear message.

## Consequences

- Gaps in the numbering (`1, 3, 4`) are normal and persist; the "ชั้น N" label is by
  position, so users never see them.
- A Layer emptied by a drag simply disappears; nothing is compacted.
- A drop before the first Layer may produce `0` or a negative value; consumers whose
  Layer Key must stay positive should lock their first Layer or validate server-side.
- The widget only guards Locked Nodes; business ordering rules (e.g. e-Saraban route
  edit refusing a step before an already-passed Stage) stay server-side and surface on
  save.
