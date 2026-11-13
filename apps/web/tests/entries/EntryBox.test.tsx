/** @jest-environment jsdom */
// jsdom has no fetch Request class, so the component gets a fake client here; the real client is covered in useExpand.test.ts.
import React from 'react';
import { act, fireEvent, screen, waitFor } from '@testing-library/react';
import { EntryBox, formatDate } from '../../src/entries/EntryBox';
import type { ApiClient } from '../../src/entries/useExpand';
import { renderApp } from '../../src/testing/render';

type Reply = { data?: unknown; error?: unknown; response: { status: number } };
const fakeClient = (reply: () => Promise<Reply>) => {
  const calls: unknown[] = [];
  const client = { POST: async (path: string, init: unknown) => { calls.push([path, init]); return reply(); } } as unknown as ApiClient;
  return { calls, client };
};
const answering = (reply: Reply) => fakeClient(async () => reply);

function type(text: string) {
  fireEvent.change(screen.getByLabelText('Short entry'), { target: { value: text } });
  fireEvent.click(screen.getByRole('button', { name: 'Expand' }));
}

describe('EntryBox', () => {
  it('sends the text as typed and shows the expanded fields', async () => {
    const entry = { code: 'F', merchant: null, category: 'Food', amount: '100.00', amount_paise: 10000, date: '2026-11-05', note: 'groceries' };
    const f = answering({ data: { ok: true, entry, error: null }, response: { status: 200 } });
    renderApp(<EntryBox client={f.client} />);
    type('F 100 5/11 groceries');
    const table = await screen.findByRole('table', { name: 'Expanded entry' });
    expect(table).toHaveTextContent('-Food100.005 Nov 2026groceries');
    expect(f.calls).toEqual([['/entries/expand', { body: { text: 'F 100 5/11 groceries' } }]]);
  });

  it('shows the rule error exactly', async () => {
    renderApp(<EntryBox client={answering({ data: { ok: false, entry: null, error: 'Unknown code "X".' }, response: { status: 200 } }).client} />);
    type('X 100');
    expect(await screen.findByRole('alert')).toHaveTextContent('Error: Unknown code "X".');
    expect(screen.queryByRole('table')).not.toBeInTheDocument();
  });

  it('shows a failed request', async () => {
    renderApp(<EntryBox client={answering({ error: { error: 'unauthorized' }, response: { status: 401 } }).client} />);
    type('F 250');
    expect(await screen.findByRole('alert')).toHaveTextContent('Could not expand the entry: unauthorized');
  });

  it('shows a loading state while the API answers', async () => {
    let answer: (r: Reply) => void = () => undefined;
    const f = fakeClient(() => new Promise<Reply>((resolve) => { answer = resolve; }));
    renderApp(<EntryBox client={f.client} />);
    type('F');
    expect(await screen.findByText('Expanding…')).toBeInTheDocument();
    await act(async () => { answer({ data: { ok: false, entry: null, error: 'Amount is missing.' }, response: { status: 200 } }); });
    await waitFor(() => expect(screen.queryByText('Expanding…')).not.toBeInTheDocument());
    expect(screen.getByRole('alert')).toHaveTextContent('Error: Amount is missing.');
  });

  it('does not submit an empty entry', () => {
    const f = answering({ data: {}, response: { status: 200 } });
    renderApp(<EntryBox client={f.client} />);
    expect(screen.getByRole('button', { name: 'Expand' })).toBeDisabled();
    fireEvent.change(screen.getByLabelText('Short entry'), { target: { value: '   ' } });
    expect(screen.getByRole('button', { name: 'Expand' })).toBeDisabled();
    expect(f.calls).toEqual([]);
  });

  it('formats calendar dates like the mock', () => {
    expect(formatDate('2026-11-05')).toBe('5 Nov 2026');
    expect(formatDate('2026-01-12')).toBe('12 Jan 2026');
  });
});
