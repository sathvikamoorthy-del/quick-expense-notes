import { pageHead, esc, table, badge } from '../../shared/components.js?v=1';
import { button } from '../../shared/form.js?v=1';
import { amt } from './expense-data.js?v=1';

export const meta = { code: 'S02', name: 'Entry box', side: 'main', icon: 'home', nav: 'Enter', roles: ['asha'] };

function resultRows(data) {
  return data.box.lines.map((line, i) => {
    if (line.error) return [String(i + 1), `<code>${esc(line.typed)}</code>`, badge(`Error: ${line.error}`, 'bad'), '', '', '', ''];
    const r = data.records[line.record];
    return [String(i + 1), `<code>${esc(line.typed)}</code>`, esc(r.merchant || '-'), esc(r.category), amt(r.amount), esc(r.date), esc(r.note)];
  });
}

export function render({ data }) {
  const { box } = data;
  const head = ['#', 'Typed', 'Merchant', 'Category', 'Amount', 'Date', 'Note'];

  if (box.stage === 'typed') {
    return `${pageHead('Note expenses')}
    <div class="card">
      <label class="field"><span>Short entries (one per line or separated by ;)</span>
        <textarea rows="4" data-toast="The entries would be expanded by the abbreviation rules.">${esc(box.text)}</textarea></label>
      <p class="note">Format: &lt;code&gt; &lt;amount&gt; [date] [note]. Today is ${esc(data.today)}.</p>
      <div class="row">
        ${button('Review', { primary: true, action: 'review' })}
        <button class="btn" data-not-defined="Whether results show while typing or after a Review action is not defined (REQ-277 open question). The mock uses a Review button.">When are results shown?</button>
      </div>
    </div>`;
  }

  if (box.stage === 'reviewed') {
    const ok = box.lines.filter((l) => !l.error).length;
    return `${pageHead('Review entries')}
      <div class="card"><p><strong>${ok} entries ready</strong>, ${box.lines.length - ok} with an error. Entries with an error are not saved.</p>
        ${table(head, resultRows(data))}
        ${button(`Save ${ok} entries`, { primary: true, action: 'save' })}
        ${button('Change the text', { toast: 'Change the text would return to the text box.' })}
      </div>`;
  }

  // saved
  const failed = box.lines.filter((l) => l.error);
  return `${pageHead('Entries saved')}
    <div class="card"><p>${badge(`${box.lines.length - failed.length} saved`, 'good')} ${badge(`${failed.length} not saved`, 'bad')}</p>
      ${table(['Typed', 'Error'], failed.map((l) => [`<code>${esc(l.typed)}</code>`, esc(l.error)]))}
      <button class="btn" data-not-defined="What happens to the text box after saving (cleared, or failed lines kept for fixing) is not defined (REQ-278 open question).">What happens to the text box?</button>
      ${button('See the November summary', { primary: true, action: 'open-summary', goto: 'S05' })}
    </div>`;
}
