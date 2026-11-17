/** @jest-environment jsdom */
import React from 'react';
import { act, fireEvent, screen } from '@testing-library/react';
import { Route, Routes } from 'react-router-dom';
import { getAuthToken, setAuthToken } from '../../src/api/client';
import { RequireAuth } from '../../src/auth/RequireAuth';
import { signOut, useSession } from '../../src/auth/useSession';
import { renderApp } from '../../src/testing/render';
import { router } from '../../src/app/router';

function show(route = '/entries') {
  renderApp(
    <Routes>
      <Route path="/sign-in" element={<p>Sign in screen</p>} />
      <Route path="/entries" element={<RequireAuth><p>Entry box</p></RequireAuth>} />
    </Routes>,
    { route }
  );
}

function signInAs(email = 'asha@example.com') {
  setAuthToken('tok');
  useSession.setState({ user: { id: 'u-1', email, display_name: 'Asha' } });
}

afterEach(() => signOut());

describe('RequireAuth', () => {
  it('shows the Sign in screen instead of the entry box when signed out', () => {
    show();
    expect(screen.getByText('Sign in screen')).toBeInTheDocument();
    expect(screen.queryByText('Entry box')).not.toBeInTheDocument();
  });

  it('shows the entry box under the S02 header when signed in', () => {
    signInAs();
    show();
    expect(screen.getByText('Entry box')).toBeInTheDocument();
    expect(screen.getByRole('banner')).toHaveTextContent('asha@example.com');
  });

  it('Sign out forgets the token and returns to the Sign in screen', () => {
    signInAs();
    show();
    fireEvent.click(screen.getByRole('button', { name: 'Sign out' }));
    expect(screen.getByText('Sign in screen')).toBeInTheDocument();
    expect(getAuthToken()).toBeNull();
    expect(useSession.getState().user).toBeNull();
  });

  it('returns to the Sign in screen when the session ends elsewhere (a 401 signs out)', () => {
    signInAs();
    show();
    act(() => signOut());
    expect(screen.getByText('Sign in screen')).toBeInTheDocument();
  });

  it('the app routes guard /entries and add /sign-in, leaving / to the not-found page', () => {
    expect(router.map((r) => r.path)).toEqual(['/sign-in', '/entries']);
  });
});
