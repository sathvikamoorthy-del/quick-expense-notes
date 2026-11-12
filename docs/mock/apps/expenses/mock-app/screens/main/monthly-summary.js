import { pageHead, esc, table } from '../../shared/components.js?v=1';
import { amt, monthSummary } from './expense-data.js?v=1';

export const meta = { code: 'S05', name: 'Monthly summary', side: 'main', icon: 'activity', nav: 'Summary', roles: ['asha'] };

export function render({ data }) {
  const { rows, grand } = monthSummary(data, data.summary.month);
  const body = rows.map(([c, v]) => [esc(c), amt(v)]);
  body.push(['<strong>Grand total</strong>', `<strong>${amt(grand)}</strong>`]);
  return `${pageHead(`Summary: ${data.summary.label}`,
      `<button class="btn" data-not-defined="How the user picks the month, and which month is shown by default, is not defined (REQ-279 open question).">Change month</button>`)}
    <div class="card">${table(['Category', 'Total'], body)}
      <p class="note">Saved entries dated in ${esc(data.summary.label)}, grouped by category. Only categories with entries are shown.</p>
      <button class="btn" data-action="open-entries" data-goto="S03">Open saved entries</button>
    </div>`;
}
