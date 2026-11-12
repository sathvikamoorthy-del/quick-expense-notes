import { pageHead, esc, table } from '../../shared/components.js?v=1';
import { amt, savedRecords } from './expense-data.js?v=1';

export const meta = { code: 'S03', name: 'Saved entries', side: 'main', icon: 'check', nav: 'Entries', roles: ['asha'] };

// The spec describes no saved-entries list (REQ-278/280/281 open questions). Plain list, columns from the record fields.
export function render({ data }) {
  const ctl = (id, kind) => {
    if (kind === 'edit' && id === data.tour.editId) return `<button class="btn" data-action="edit-entry" data-goto="S04">Edit</button>`;
    if (kind === 'delete' && id === data.tour.deleteId) return `<button class="btn btn-danger" data-action="delete-entry">Delete</button>`;
    return kind === 'edit'
      ? `<button class="btn" data-toast="Edit would open this entry for correcting.">Edit</button>`
      : `<button class="btn btn-danger" data-toast="Delete would remove this entry.">Delete</button>`;
  };
  const rows = savedRecords(data).map((r) => [
    esc(r.merchant || '-'), esc(r.category), amt(r.amount), esc(r.date), esc(r.note), `${ctl(r.id, 'edit')} ${ctl(r.id, 'delete')}`
  ]);
  return `${pageHead('Saved entries', `<button class="btn" data-not-defined="The spec describes no list of saved entries: where it is, its columns, order and filters are not defined (REQ-278, REQ-280, REQ-281 open questions).">About this list</button>`)}
    <div class="card">${table(['Merchant', 'Category', 'Amount', 'Date', 'Note', ''], rows)}
      <p class="note">${rows.length} saved entries.</p>
      <button class="btn" data-action="open-summary" data-goto="S05">See the November summary</button>
    </div>`;
}
