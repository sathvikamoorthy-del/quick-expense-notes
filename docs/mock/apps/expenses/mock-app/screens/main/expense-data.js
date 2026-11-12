// Helpers shared by the expense screens (not a screen; not registered).
// Amounts: rupees with 2 decimals (02-abbreviation-rules.md, Amount).
export const amt = (n) => Number(n).toFixed(2);

// Category order follows the sample summary in 03-sample-entries.md. The spec does not define
// the order (REQ-279 open question); Utilities and Other are appended (see gaps).
export const CATEGORY_ORDER = ['Food', 'Travel', 'Rent', 'Entertainment', 'Health', 'Shopping', 'Utilities', 'Other'];

// Saved records of the signed-in user: saved and not deleted.
export const savedRecords = (data) =>
  Object.entries(data.records ?? {})
    .filter(([, r]) => r.saved && !r.deleted)
    .map(([id, r]) => ({ id, ...r }));

// Monthly summary: group the month's saved records by category; only categories with entries.
export function monthSummary(data, month) {
  const totals = {};
  for (const r of savedRecords(data).filter((x) => x.month === month)) totals[r.category] = (totals[r.category] ?? 0) + Number(r.amount);
  const rows = CATEGORY_ORDER.filter((c) => c in totals).map((c) => [c, totals[c]]);
  return { rows, grand: rows.reduce((s, [, v]) => s + v, 0) };
}
