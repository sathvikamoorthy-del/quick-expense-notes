import { pageHead, esc, table } from '../../shared/components.js?v=1';
import { button } from '../../shared/form.js?v=1';
import { amt } from './expense-data.js?v=1';

export const meta = { code: 'S04', name: 'Edit entry', side: 'main', roles: ['asha'] };

// The edit form is not defined (REQ-280 open question): short form or field by field. The mock shows the short form.
export function render({ data }) {
  const r = data.records[data.tour.editId];
  const head = ['Merchant', 'Category', 'Amount', 'Date', 'Note'];
  return `${pageHead('Edit entry')}
    <div class="card"><p><strong>Now saved</strong></p>
      ${table(head, [[esc(r.merchant || '-'), esc(r.category), amt(r.amount), esc(r.date), esc(r.note)]])}</div>
    <div class="card">
      <label class="field"><span>Corrected entry (short form)</span>
        <input value="${esc(data.edit.newTyped)}" data-not-defined="Whether an entry is edited by re-typing the short form or field by field is not defined (REQ-280 open question). The mock shows the short form."></label>
      <p class="note">Expands to: ${esc(r.merchant || '-')}, ${esc(r.category)}, ${amt(data.edit.newAmount)}, ${esc(r.date)}, ${esc(r.note)}</p>
      ${button('Save change', { primary: true, action: 'save-edit', goto: 'S03' })}
      ${button('Cancel', { toast: 'Cancel would return to the saved entries without changing anything.' })}
    </div>`;
}
