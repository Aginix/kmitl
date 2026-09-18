# Budget code selection is scoped by the approval category and restricted to non-procurement codes

The budget code a request may reserve against is the approval category's concern, not a free choice re-derived on every request. When a category pins a `budget_account_id` the request is constrained to exactly that code across all selection surfaces — the reservation picker, the picker write-back, and the draw-down of an existing reservation (`budget.commitment`); when the category leaves it blank the request selects from the full baseline. This is folded into a single choke point (`_reservation_account_domain`) rather than enforced with a defensive `@api.constrains`, which would strand older requests whose code no longer matches a since-edited category.

The baseline itself is corrected here: approval requests select **non-procurement** expense codes (`budgetable`, `budget_type = expense`, `purchase_ok = False`), dropping the inherited `product_id != False` requirement. The prior domain (`purchase_ok = True`, product-backed) was cargo-culted from `purchase.request`, but an approval is not a procurement — its lines pick products from the category's `allowed_product_ids`, and neither commitment creation nor the downstream disbursement (`[budgetable, expense]`) needs the code to carry a product. Restricting to `purchase_ok = False` keeps procurement codes reserved through purchase flows and expense/operating codes through approval, so a single code is never double-reserved from two apps.

## Considered Options

- **Match the disbursement domain (`[budgetable, expense]`, any `purchase_ok`)** — rejected: leaves procurement codes reservable from both purchase and approval, inviting double reservation.
- **Category pin overrides the baseline (allow a non-purchasable/any code once pinned)** — rejected: the category's `budget_account_id` domain is tightened to the same non-procurement set instead, so a pin is always usable and misconfiguration is blocked at config time, not discovered at reserve time.

## Consequences

- Dimensions (ส่วนงาน/แหล่งเงิน/กองทุน/กิจกรรม) are **not** locked by the category in this round — they remain adjustable defaults. Locking them would require changes to the JS reservation picker; a server-side check that reserved dimensions match category-pinned ones can be added later without touching the picker.
- Draw-down reservation **visibility** now equals drawability (filtered by budget code only, consistent with dimensions being unlocked), narrowing the dropdown to non-procurement codes even when the category is blank.
- Single pinned code only; expanding a category to a *set* of allowed codes (mirroring `allowed_product_ids`) is deferred until a real multi-code need appears.
