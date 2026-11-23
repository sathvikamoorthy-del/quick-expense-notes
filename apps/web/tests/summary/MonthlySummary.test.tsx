/** @jest-environment jsdom */
// jsdom has no fetch Request class, so the page gets a fake client here; the real client is covered in useSummary.test.ts.
import React from 'react';
import { act, fireEvent, screen, waitFor, within } from '@testing-library/react';
import type { ApiClient } from '../../src/entries/useExpand';
import { MonthlySummary, monthLabel, shiftMonth } from '../../src/summary/MonthlySummary';
import { renderApp } from '../../src/testing/render';

type Reply = { data?: unknown; error?: unknown; response: { status: number } };
const fakeClient = (reply: (month: string | undefined) => Promise<Reply>) => {
  const months: (string | undefined)[] = [];
  const client = {
    GET: async (_path: string, init: { params?: { query?: { month?: string } } }) => {
      const month = init?.params?.query?.month;
      months.push(month);
      return reply(month);
    },
  } as unknown as ApiClient;
  return { months, client };
};

const total = (code: string, category: string, paise: number) => ({
  code,
  category,
  total: (paise / 100).toFixed(2),
  total_paise: paise,
});

// The REQ-279 acceptance month: the 8 working sample entries saved.
const NOVEMBER = {
  month: '2026-11',
  current_month: '2026-11',
  categories: [
    total('F', 'Food', 59000),
    total('T', 'Travel', 18000),
    total('R', 'Rent', 150000),
    total('E', 'Entertainment', 64900),
    total('H', 'Health', 42000),
    total('S', 'Shopping', 279950),
  ],
  grand_total: '6138.50',
  grand_total_paise: 613850,
};
const empty = (month: string) => ({ month, current_month: '2026-11', categories: [], grand_total: '0.00', grand_total_paise: 0 });
/** November for the first load (no month), an empty month otherwise. */
const months = () =>
  fakeClient(async (month) => ({ data: month === undefined || month === '2026-11' ? NOVEMBER : empty(month), response: { status: 200 } }));

describe('MonthlySummary', () => {
  it('opens on the current month and shows the sample totals in order with the grand total', async () => {
    const f = months();
    renderApp(<MonthlySummary client={f.client} />);
    const table = await screen.findByRole('table', { name: 'Summary for November 2026' });
    expect(screen.getByRole('heading', { name: 'November 2026' })).toBeInTheDocument();
    expect(within(table).getAllByRole('row').map((r) => r.textContent)).toEqual([
      'CategoryTotal',
      'Food590.00',
      'Travel180.00',
      'Rent1500.00',
      'Entertainment649.00',
      'Health420.00',
      'Shopping2799.50',
      'Grand total6138.50',
    ]);
    expect(f.months).toEqual([undefined]);
  });

  it('shows the no-expenses text, with no table and no grand total, for an empty month', async () => {
    renderApp(<MonthlySummary client={months().client} />);
    await screen.findByRole('table');
    fireEvent.click(screen.getByRole('button', { name: 'Previous' }));
    expect(await screen.findByText('No expenses in this month.')).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'October 2026' })).toBeInTheDocument();
    expect(screen.queryByRole('table')).not.toBeInTheDocument();
    expect(screen.queryByText(/Grand total/)).not.toBeInTheDocument();
  });

  it('disables Next on the current month, and Previous then Next comes back', async () => {
    const f = months();
    renderApp(<MonthlySummary client={f.client} />);
    await screen.findByRole('table');
    expect(screen.getByRole('button', { name: 'Next' })).toBeDisabled();
    fireEvent.click(screen.getByRole('button', { name: 'Previous' }));
    await screen.findByText('No expenses in this month.');
    expect(screen.getByRole('button', { name: 'Next' })).toBeEnabled();
    fireEvent.click(screen.getByRole('button', { name: 'Next' }));
    await screen.findByRole('table', { name: 'Summary for November 2026' });
    expect(screen.getByRole('button', { name: 'Next' })).toBeDisabled();
    expect(f.months).toEqual([undefined, '2026-10', '2026-11']);
  });

  it('shows loading, then a failed request', async () => {
    let answer: (r: Reply) => void = () => undefined;
    renderApp(<MonthlySummary client={fakeClient(() => new Promise<Reply>((resolve) => { answer = resolve; })).client} />);
    expect(screen.getByText('Loading…')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Previous' })).toBeDisabled();
    await act(async () => { answer({ error: { error: 'unauthorized' }, response: { status: 401 } }); });
    await waitFor(() => expect(screen.getByRole('alert')).toHaveTextContent('Could not load the summary: unauthorized'));
  });

  it('links back to the entry box', async () => {
    renderApp(<MonthlySummary client={months().client} />);
    await screen.findByRole('table');
    expect(screen.getByRole('link', { name: 'Enter expenses' })).toHaveAttribute('href', '/entries');
    expect(screen.getByRole('link', { name: 'Saved entries' })).toHaveAttribute('href', '/saved-entries'); // WI-052
  });

  it('names months and moves between them across years', () => {
    expect(monthLabel('2026-11')).toBe('November 2026');
    expect(monthLabel('2027-01')).toBe('January 2027');
    expect(shiftMonth('2026-11', -1)).toBe('2026-10');
    expect(shiftMonth('2026-01', -1)).toBe('2025-12');
    expect(shiftMonth('2026-12', 1)).toBe('2027-01');
  });
});
