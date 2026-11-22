/** @jest-environment jsdom */
// jsdom has no fetch Request class, so the component gets a fake client here; the real client is covered in useExpand.test.ts.
import React from 'react';
import { act, fireEvent, screen, waitFor, within } from '@testing-library/react';
import { EntryBox, formatDate, savedMessage } from '../../src/entries/EntryBox';
import type { ApiClient } from '../../src/entries/useExpand';
import { renderApp } from '../../src/testing/render';

type Reply = { data?: unknown; error?: unknown; response: { status: number } };
const fakeClient = (reply: (path: string) => Promise<Reply>) => {
  const calls: unknown[] = [];
  const client = { POST: async (path: string, init: unknown) => { calls.push([path, init]); return reply(path); } } as unknown as ApiClient;
  return { calls, client };
};
const answering = (reply: Reply) => fakeClient(async () => reply);
/** One reply per path; /entries/save replies are used in turn. */
const routed = (expandReply: unknown, ...saveReplies: Reply[]) =>
  fakeClient(async (path) =>
    path === '/entries/save' ? (saveReplies.shift() as Reply) : { data: expandReply, response: { status: 200 } });
const saveButton = () => screen.getByRole('button', { name: 'Save' });

function typeText(text: string) {
  fireEvent.change(screen.getByLabelText('Short entries'), { target: { value: text } });
}
function expand(text: string) {
  typeText(text);
  fireEvent.click(screen.getByRole('button', { name: 'Expand' }));
}

const entry = (code: string, merchant: string | null, category: string, amount: string, date: string, note: string | null = null) =>
  ({ code, merchant, category, amount, amount_paise: Math.round(Number(amount) * 100), date, note });

// The 03-sample-entries.md text box (today = 12 Nov 2026), as the API answers it.
const SAMPLE = 'F 250; SWG 340 yd\nX 100\nUBR 180 12/11 airport';
const SAMPLE_REPLY = {
  ok: true,
  error: null,
  results: [
    { typed: 'F 250', ok: true, entry: entry('F', null, 'Food', '250.00', '2026-11-12'), error: null },
    { typed: 'SWG 340 yd', ok: true, entry: entry('SWG', 'Swiggy', 'Food', '340.00', '2026-11-11'), error: null },
    { typed: 'X 100', ok: false, entry: null, error: 'Unknown code "X".' },
    { typed: 'UBR 180 12/11 airport', ok: true, entry: entry('UBR', 'Uber', 'Travel', '180.00', '2026-11-12', 'airport'), error: null },
  ],
};

describe('EntryBox', () => {
  it('sends the whole text box as typed and shows one row per entry, errors included', async () => {
    const f = answering({ data: SAMPLE_REPLY, response: { status: 200 } });
    renderApp(<EntryBox client={f.client} />);
    expand(SAMPLE);
    const table = await screen.findByRole('table', { name: 'Expanded entries' });
    const rows = within(table).getAllByRole('row').slice(1);
    expect(rows.map((row) => row.textContent)).toEqual([
      '1F 250-Food250.0012 Nov 2026',
      '2SWG 340 ydSwiggyFood340.0011 Nov 2026',
      '3X 100Error: Unknown code "X".',
      '4UBR 180 12/11 airportUberTravel180.0012 Nov 2026airport',
    ]);
    expect(f.calls).toEqual([['/entries/expand-all', { body: { text: SAMPLE } }]]);
  });

  it('does not send anything before Expand is pressed', async () => {
    const f = answering({ data: SAMPLE_REPLY, response: { status: 200 } });
    renderApp(<EntryBox client={f.client} />);
    await act(async () => undefined); // the hook's first (empty) answer
    typeText(SAMPLE);
    expect(f.calls).toEqual([]);
    expect(screen.queryByRole('table')).not.toBeInTheDocument();
  });

  it('shows a rejected text box (too many entries) as an alert with no table', async () => {
    renderApp(<EntryBox client={answering({ data: { ok: false, error: 'Too many entries (max 20).', results: [] }, response: { status: 200 } }).client} />);
    expand(Array(21).fill('F 1').join('\n'));
    expect(await screen.findByRole('alert')).toHaveTextContent('Error: Too many entries (max 20).');
    expect(screen.queryByRole('table')).not.toBeInTheDocument();
  });

  it('shows a failed request', async () => {
    renderApp(<EntryBox client={answering({ error: { error: 'unauthorized' }, response: { status: 401 } }).client} />);
    expand('F 250');
    expect(await screen.findByRole('alert')).toHaveTextContent('Could not expand the entries: unauthorized');
  });

  it('shows a loading state while the API answers', async () => {
    let answer: (r: Reply) => void = () => undefined;
    const f = fakeClient(() => new Promise<Reply>((resolve) => { answer = resolve; }));
    renderApp(<EntryBox client={f.client} />);
    expand('F');
    expect(await screen.findByText('Expanding…')).toBeInTheDocument();
    await act(async () => {
      answer({ data: { ok: true, error: null, results: [{ typed: 'F', ok: false, entry: null, error: 'Amount is missing.' }] }, response: { status: 200 } });
    });
    await waitFor(() => expect(screen.queryByText('Expanding…')).not.toBeInTheDocument());
    expect(screen.getByRole('table', { name: 'Expanded entries' })).toHaveTextContent('Error: Amount is missing.');
  });

  it('does not submit a text box with no entries', async () => {
    const f = answering({ data: {}, response: { status: 200 } });
    renderApp(<EntryBox client={f.client} />);
    await act(async () => undefined); // the hook's first (empty) answer
    expect(screen.getByRole('button', { name: 'Expand' })).toBeDisabled();
    for (const blank of ['   ', ' ;\n ;; ', '\n\n']) {
      typeText(blank);
      expect(screen.getByRole('button', { name: 'Expand' })).toBeDisabled();
    }
    expect(f.calls).toEqual([]);
  });

  describe('saving (REQ-278)', () => {
    const saved3 = { ok: true, error: null, saved: 3, ids: ['a', 'b', 'c'], failed: [SAMPLE_REPLY.results[2]] };

    it('cannot save before a review, and nothing is posted to /entries/save before Save is pressed', async () => {
      const f = routed(SAMPLE_REPLY);
      renderApp(<EntryBox client={f.client} />);
      typeText(SAMPLE);
      expect(saveButton()).toBeDisabled();
      fireEvent.click(screen.getByRole('button', { name: 'Expand' }));
      await screen.findByRole('table', { name: 'Expanded entries' });
      expect(saveButton()).toBeEnabled();
      expect(f.calls.map((c) => (c as unknown[])[0])).toEqual(['/entries/expand-all']);
    });

    it('saves the valid entries, says how many failed, and keeps only the failed lines in the box', async () => {
      const f = routed(SAMPLE_REPLY, { data: saved3, response: { status: 200 } });
      renderApp(<EntryBox client={f.client} />);
      expand(SAMPLE);
      await screen.findByRole('table', { name: 'Expanded entries' });
      fireEvent.click(saveButton());
      expect(await screen.findByRole('status')).toHaveTextContent('3 entries saved, 1 not saved.');
      expect(screen.getByText('X 100', { selector: 'span' }).parentElement).toHaveTextContent('X 100: Error: Unknown code "X".');
      expect(screen.getByLabelText('Short entries')).toHaveValue('X 100');
      expect(screen.queryByRole('table')).not.toBeInTheDocument();
      expect(saveButton()).toBeDisabled();
      expect(f.calls[1]).toEqual(['/entries/save', { body: { text: SAMPLE, reviewed: SAMPLE_REPLY.results } }]);
    });

    it('clears the box when every entry was saved', async () => {
      const allValid = { ...SAMPLE_REPLY, results: SAMPLE_REPLY.results.filter((r) => r.ok) };
      const f = routed(allValid, { data: { ok: true, error: null, saved: 3, ids: ['a', 'b', 'c'], failed: [] }, response: { status: 200 } });
      renderApp(<EntryBox client={f.client} />);
      expand('F 250; SWG 340 yd\nUBR 180 12/11 airport');
      await screen.findByRole('table', { name: 'Expanded entries' });
      fireEvent.click(saveButton());
      expect(await screen.findByRole('status')).toHaveTextContent(/^3 entries saved\.$/);
      expect(screen.getByLabelText('Short entries')).toHaveValue('');
    });

    it('cannot save once the text changed after the review', async () => {
      renderApp(<EntryBox client={routed(SAMPLE_REPLY).client} />);
      expand(SAMPLE);
      await screen.findByRole('table', { name: 'Expanded entries' });
      typeText(`${SAMPLE}\nF 10`);
      expect(saveButton()).toBeDisabled();
    });

    it('cannot save a review where every entry has an error', async () => {
      const onlyErrors = { ok: true, error: null, results: [SAMPLE_REPLY.results[2]] };
      renderApp(<EntryBox client={routed(onlyErrors).client} />);
      expand('X 100');
      await screen.findByRole('table', { name: 'Expanded entries' });
      expect(saveButton()).toBeDisabled();
    });

    it('shows a refused save and keeps the review, and Expand reviews the same text again', async () => {
      const refused = { ok: false, error: 'The entries changed since the review. Press Expand to review them again.', saved: 0, ids: [], failed: [] };
      const f = routed(SAMPLE_REPLY, { data: refused, response: { status: 200 } });
      renderApp(<EntryBox client={f.client} />);
      expand(SAMPLE);
      await screen.findByRole('table', { name: 'Expanded entries' });
      fireEvent.click(saveButton());
      expect(await screen.findByRole('alert')).toHaveTextContent('Error: The entries changed since the review. Press Expand to review them again.');
      expect(screen.getByRole('table', { name: 'Expanded entries' })).toBeInTheDocument();
      expect(screen.getByLabelText('Short entries')).toHaveValue(SAMPLE);
      fireEvent.click(screen.getByRole('button', { name: 'Expand' }));
      await waitFor(() => expect(f.calls.map((c) => (c as unknown[])[0])).toEqual(['/entries/expand-all', '/entries/save', '/entries/expand-all']));
      await waitFor(() => expect(screen.queryByRole('alert')).not.toBeInTheDocument());
    });

    it('shows a failed save request', async () => {
      const f = routed(SAMPLE_REPLY, { error: { error: 'unauthorized' }, response: { status: 401 } });
      renderApp(<EntryBox client={f.client} />);
      expand(SAMPLE);
      await screen.findByRole('table', { name: 'Expanded entries' });
      fireEvent.click(saveButton());
      expect(await screen.findByRole('alert')).toHaveTextContent('Could not save the entries: unauthorized');
    });

    it('words the saved message', () => {
      expect(savedMessage(1, 0)).toBe('1 entry saved.');
      expect(savedMessage(3, 1)).toBe('3 entries saved, 1 not saved.');
      expect(savedMessage(0, 2)).toBe('0 entries saved, 2 not saved.');
    });
  });

  it('formats calendar dates like the mock', () => {
    expect(formatDate('2026-11-05')).toBe('5 Nov 2026');
    expect(formatDate('2026-01-12')).toBe('12 Jan 2026');
  });
});
