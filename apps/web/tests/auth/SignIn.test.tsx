/** @jest-environment jsdom */
// jsdom has no fetch Request class, so the screen gets a fake client here; the real client is covered in useSession.test.ts.
import React from 'react';
import { fireEvent, screen, waitFor } from '@testing-library/react';
import { Route, Routes } from 'react-router-dom';
import { getAuthToken } from '../../src/api/client';
import { SignIn } from '../../src/auth/SignIn';
import { type ApiClient, signOut, useSession } from '../../src/auth/useSession';
import { renderApp } from '../../src/testing/render';

type Reply = { data?: unknown; error?: unknown; response: { status: number } };
const answering = (reply: Reply) => {
  const calls: unknown[] = [];
  const client = { POST: async (path: string, init: unknown) => { calls.push([path, init]); return reply; } } as unknown as ApiClient;
  return { calls, client };
};
const user = { id: 'u-1', email: 'asha@example.com', display_name: 'Asha' };
const signedIn = () => answering({ data: { token: 'tok', expires_in: 3600, user }, response: { status: 200 } });

function show(client: ApiClient) {
  renderApp(
    <Routes>
      <Route path="/sign-in" element={<SignIn client={client} />} />
      <Route path="/entries" element={<p>Entry box</p>} />
    </Routes>,
    { route: '/sign-in' }
  );
}

function fill(email: string, password: string) {
  fireEvent.change(screen.getByLabelText('Email'), { target: { value: email } });
  fireEvent.change(screen.getByLabelText('Password (at least 8 characters)'), { target: { value: password } });
  fireEvent.click(screen.getByRole('button', { name: 'Sign in' }));
}

afterEach(() => signOut());

describe('SignIn', () => {
  it('shows the S01 screen with no sign-up, forgot password or other providers', () => {
    show(signedIn().client);
    expect(screen.getByText('Sign in to see and change only your own expenses.')).toBeInTheDocument();
    expect(screen.getAllByRole('button').map((b) => b.textContent)).toEqual(['Sign in']);
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
  });

  it('signs in with the details as typed and goes to the entry box', async () => {
    const f = signedIn();
    show(f.client);
    fill('Asha@Example.com', 'correct-horse-1');
    expect(await screen.findByText('Entry box')).toBeInTheDocument();
    expect(f.calls).toEqual([['/auth/sign-in', { body: { email: 'Asha@Example.com', password: 'correct-horse-1' } }]]);
    expect(getAuthToken()).toBe('tok');
    expect(useSession.getState().user).toEqual(user);
  });

  it('shows Invalid email or password. when the API refuses the details', async () => {
    show(answering({ error: { error: 'Invalid email or password.' }, response: { status: 401 } }).client);
    fill('asha@example.com', 'wrong-password');
    expect(await screen.findByRole('alert')).toHaveTextContent('Invalid email or password.');
    expect(screen.queryByText('Entry box')).not.toBeInTheDocument();
    expect(getAuthToken()).toBeNull();
  });

  it('empty email or password shows Invalid email or password.', async () => {
    const f = signedIn();
    show(f.client);
    fill('', 'correct-horse-1');
    expect(await screen.findByRole('alert')).toHaveTextContent('Invalid email or password.');
    fill('asha@example.com', '');
    await waitFor(() => expect(screen.getByRole('alert')).toHaveTextContent('Invalid email or password.'));
    expect(f.calls).toEqual([]);
    expect(screen.getByRole('button', { name: 'Sign in' })).toBeInTheDocument();
    expect(screen.queryByText('Entry box')).not.toBeInTheDocument();
  });
});
