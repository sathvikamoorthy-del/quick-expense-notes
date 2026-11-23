/** @jest-environment jsdom */
// jsdom has no fetch Request class, so the page gets a fake client here; the real client is covered in useSavedEntries.test.ts.
import React from 'react';
import { act, fireEvent, screen, waitFor, within } from '@testing-library/react';
import type { ApiClient } from '../../src/entries/useExpand';
import { SavedEntries } from '../../src/saved/SavedEntries';
import { renderApp } from '../../src/testing/render';

type Reply = { data?: unknown; error?: unknown; response: { status: number } };
type Entry = { id: string; typed: string; code: string; merchant: string | null; category: string; amount: string; amount_paise: number; date: string; note: string | null };

const entry = (n: number, typed: string, merchant: string | null, category: string, amount: string, date: string, note: string | null = null): Entry =>
  ({ id: `id-${n}`, typed, code: typed.split(' ')[0], merchant, category, amount, amount_paise: Math.round(Number(amount) * 100), date, note });

const UBR = entry(1, 'UBR 180 12/11 airport', 'Uber', 'Travel', '180.00', '2026-11-12', 'airport');
const SWG = entry(2, 'SWG 340 yd', 'Swiggy', 'Food', '340.00', '2026-11-11');

/** A tiny fake API: GET /entries serves `store` by month; PUT answers with `edits` in turn and applies successful ones;
 * DELETE removes the entry (204), or answers 404 for one that is not in the store, or `deleteFails` when set. */
function fakeApi(store: Entry[], ...edits: Reply[]) {
  return fakeApiWith({ store, edits });
}

function fakeApiWith({ store, edits = [], deleteFails }: { store: Entry[]; edits?: Reply[]; deleteFails?: Reply }) {
  const calls: unknown[][] = [];
  const client = {
    GET: async (_path: string, init: { params?: { query?: { month?: string } } }) => {
      const month = init?.params?.query?.month ?? '2026-11';
      calls.push(['GET', month]);
      const entries = store.filter((e) => e.date.startsWith(month)).sort((a, b) => b.date.localeCompare(a.date));
      return { data: { month, current_month: '2026-11', entries }, response: { status: 200 } };
    },
    PUT: async (_path: string, init: { params: { path: { expense_id: string } }; body: { text: string } }) => {
      calls.push(['PUT', init.params.path.expense_id, init.body.text]);
      const reply = edits.shift() as Reply;
      const updated = (reply.data as { ok?: boolean; entry?: Entry } | undefined)?.entry;
      if (updated) store.splice(store.findIndex((e) => e.id === updated.id), 1, updated);
      return reply;
    },
    DELETE: async (_path: string, init: { params: { path: { expense_id: string } } }) => {
      const id = init.params.path.expense_id;
      calls.push(['DELETE', id]);
      if (deleteFails) return { ...deleteFails, response: { ...deleteFails.response, ok: false } };
      const index = store.findIndex((e) => e.id === id);
      if (index < 0) return { error: { error: 'not-found' }, response: { status: 404, ok: false } };
      store.splice(index, 1);
      return { response: { status: 204, ok: true } };
    },
  } as unknown as ApiClient;
  return { calls, client };
}

const rowsOf = () => within(screen.getByRole('table')).getAllByRole('row').slice(1).map((r) => r.textContent);
const editButtons = () => screen.getAllByRole('button', { name: 'Edit' });
const deleteButtons = () => screen.getAllByRole('button', { name: 'Delete' });

describe('SavedEntries', () => {
  it('shows the current month newest date first, with links to the entry box and the summary', async () => {
    renderApp(<SavedEntries client={fakeApi([SWG, UBR]).client} />);
    await screen.findByRole('table', { name: 'Saved entries of November 2026' });
    expect(screen.getByRole('heading', { name: 'November 2026' })).toBeInTheDocument();
    expect(rowsOf()).toEqual([
      'UBR 180 12/11 airportUberTravel180.0012 Nov 2026airportEditDelete',
      'SWG 340 ydSwiggyFood340.0011 Nov 2026EditDelete',
    ]);
    expect(screen.getByRole('link', { name: 'Enter expenses' })).toHaveAttribute('href', '/entries');
    expect(screen.getByRole('link', { name: 'Monthly summary' })).toHaveAttribute('href', '/summary');
  });

  it('edits a row in place: pre-filled with the typed text, saved, then the row shows the new values', async () => {
    const updated = { ...UBR, typed: 'UBR 220 12/11 airport', amount: '220.00', amount_paise: 22000 };
    const f = fakeApi([UBR, SWG], { data: { ok: true, error: null, entry: updated }, response: { status: 200 } });
    renderApp(<SavedEntries client={f.client} />);
    await screen.findByRole('table');
    fireEvent.click(editButtons()[0]);
    const input = screen.getByLabelText('Edit entry');
    expect(input).toHaveValue('UBR 180 12/11 airport');
    fireEvent.change(input, { target: { value: 'UBR 220 12/11 airport' } });
    fireEvent.click(screen.getByRole('button', { name: 'Save' }));
    await waitFor(() => expect(rowsOf()[0]).toBe('UBR 220 12/11 airportUberTravel220.0012 Nov 2026airportEditDelete'));
    expect(screen.queryByLabelText('Edit entry')).not.toBeInTheDocument();
    expect(f.calls).toContainEqual(['PUT', 'id-1', 'UBR 220 12/11 airport']);
  });

  it('keeps edit mode and shows the rule error when the edit is refused', async () => {
    const f = fakeApi([UBR], { data: { ok: false, error: 'Unknown code "X".', entry: null }, response: { status: 200 } });
    renderApp(<SavedEntries client={f.client} />);
    await screen.findByRole('table');
    fireEvent.click(editButtons()[0]);
    fireEvent.change(screen.getByLabelText('Edit entry'), { target: { value: 'X 100' } });
    fireEvent.click(screen.getByRole('button', { name: 'Save' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('Error: Unknown code "X".');
    expect(screen.getByLabelText('Edit entry')).toHaveValue('X 100');
  });

  it('shows a failed edit request', async () => {
    renderApp(<SavedEntries client={fakeApi([UBR], { error: { error: 'not-found' }, response: { status: 404 } }).client} />);
    await screen.findByRole('table');
    fireEvent.click(editButtons()[0]);
    fireEvent.click(screen.getByRole('button', { name: 'Save' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('Could not save the edit: not-found');
  });

  it('Cancel restores the row unchanged, and only one row is edited at a time', async () => {
    const f = fakeApi([UBR, SWG]);
    renderApp(<SavedEntries client={f.client} />);
    await screen.findByRole('table');
    fireEvent.click(editButtons()[0]);
    expect(editButtons().every((b) => (b as HTMLButtonElement).disabled)).toBe(true);
    fireEvent.change(screen.getByLabelText('Edit entry'), { target: { value: 'F 1' } });
    fireEvent.click(screen.getByRole('button', { name: 'Cancel' }));
    expect(rowsOf()[0]).toBe('UBR 180 12/11 airportUberTravel180.0012 Nov 2026airportEditDelete');
    expect(f.calls.filter((c) => c[0] === 'PUT')).toEqual([]);
  });

  it('says where an entry went when the edit moves it to another month', async () => {
    const moved = { ...SWG, typed: 'SWG 340 30/10', date: '2026-10-30' };
    renderApp(<SavedEntries client={fakeApi([UBR, SWG], { data: { ok: true, error: null, entry: moved }, response: { status: 200 } }).client} />);
    await screen.findByRole('table');
    fireEvent.click(editButtons()[1]);
    fireEvent.change(screen.getByLabelText('Edit entry'), { target: { value: 'SWG 340 30/10' } });
    fireEvent.click(screen.getByRole('button', { name: 'Save' }));
    expect(await screen.findByRole('status')).toHaveTextContent('The entry moved to October 2026.');
    await waitFor(() => expect(rowsOf()).toEqual(['UBR 180 12/11 airportUberTravel180.0012 Nov 2026airportEditDelete']));
  });

  it('moves between months like the summary, with Next disabled on the current month', async () => {
    const f = fakeApi([UBR]);
    renderApp(<SavedEntries client={f.client} />);
    await screen.findByRole('table');
    expect(screen.getByRole('button', { name: 'Next' })).toBeDisabled();
    fireEvent.click(screen.getByRole('button', { name: 'Previous' }));
    expect(await screen.findByText('No saved entries in this month.')).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'October 2026' })).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Next' }));
    await screen.findByRole('table', { name: 'Saved entries of November 2026' });
    expect(f.calls.filter((c) => c[0] === 'GET')).toEqual([['GET', '2026-11'], ['GET', '2026-10'], ['GET', '2026-11']]);
  });

  describe('deleting (REQ-281)', () => {
    const NFX = entry(3, 'NFX 649', 'Netflix', 'Entertainment', '649.00', '2026-11-12');

    it('asks for confirmation in the row, with the other rows locked', async () => {
      const f = fakeApi([UBR, NFX, SWG]);
      renderApp(<SavedEntries client={f.client} />);
      await screen.findByRole('table');
      fireEvent.click(deleteButtons()[1]); // NFX
      const confirm = screen.getByText('Delete this entry?').closest('tr') as HTMLElement;
      expect(confirm).toHaveTextContent('NFX 649');
      expect(within(confirm).getByRole('button', { name: 'Delete' })).toBeEnabled();
      expect(editButtons().every((b) => (b as HTMLButtonElement).disabled)).toBe(true);
      const others = deleteButtons().filter((b) => !confirm.contains(b));
      expect(others.every((b) => (b as HTMLButtonElement).disabled)).toBe(true);
      expect(f.calls.filter((c) => c[0] === 'DELETE')).toEqual([]);
    });

    it('Cancel restores the row and deletes nothing', async () => {
      const f = fakeApi([UBR, NFX]);
      renderApp(<SavedEntries client={f.client} />);
      await screen.findByRole('table');
      fireEvent.click(deleteButtons()[1]);
      fireEvent.click(screen.getByRole('button', { name: 'Cancel' }));
      expect(screen.queryByText('Delete this entry?')).not.toBeInTheDocument();
      expect(rowsOf()).toHaveLength(2);
      expect(f.calls.filter((c) => c[0] === 'DELETE')).toEqual([]);
    });

    it('confirming deletes the entry: the row is gone and the note says so', async () => {
      const f = fakeApi([UBR, NFX, SWG]);
      renderApp(<SavedEntries client={f.client} />);
      await screen.findByRole('table');
      fireEvent.click(deleteButtons()[1]);
      const confirm = screen.getByText('Delete this entry?').closest('tr') as HTMLElement;
      fireEvent.click(within(confirm).getByRole('button', { name: 'Delete' }));
      expect(await screen.findByRole('status')).toHaveTextContent('Entry deleted.');
      await waitFor(() => expect(rowsOf().some((r) => r?.startsWith('NFX 649'))).toBe(false));
      expect(rowsOf()).toHaveLength(2);
      expect(f.calls).toContainEqual(['DELETE', 'id-3']);
    });

    it('a failed delete keeps the confirmation and shows the error', async () => {
      const f = fakeApiWith({ store: [UBR], deleteFails: { error: { error: 'unauthorized' }, response: { status: 401 } } });
      renderApp(<SavedEntries client={f.client} />);
      await screen.findByRole('table');
      fireEvent.click(deleteButtons()[0]);
      const confirm = screen.getByText('Delete this entry?').closest('tr') as HTMLElement;
      fireEvent.click(within(confirm).getByRole('button', { name: 'Delete' }));
      expect(await screen.findByRole('alert')).toHaveTextContent('Could not delete the entry: unauthorized');
      expect(screen.getByText('Delete this entry?')).toBeInTheDocument();
      expect(rowsOf()).toHaveLength(1);
    });

    it('an open edit locks the Delete buttons of the other rows', async () => {
      renderApp(<SavedEntries client={fakeApi([UBR, SWG]).client} />);
      await screen.findByRole('table');
      fireEvent.click(editButtons()[0]);
      expect(deleteButtons().every((b) => (b as HTMLButtonElement).disabled)).toBe(true);
    });
  });

  it('shows loading, then a failed list request', async () => {
    let answer: (r: Reply) => void = () => undefined;
    const client = { GET: () => new Promise<Reply>((resolve) => { answer = resolve; }) } as unknown as ApiClient;
    renderApp(<SavedEntries client={client} />);
    expect(screen.getByText('Loading…')).toBeInTheDocument();
    await act(async () => { answer({ error: { error: 'unauthorized' }, response: { status: 401 } }); });
    await waitFor(() => expect(screen.getByRole('alert')).toHaveTextContent('Could not load the saved entries: unauthorized'));
  });
});
