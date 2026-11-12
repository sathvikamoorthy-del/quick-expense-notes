import { pageHead, esc } from '../../shared/components.js?v=1';
import { button } from '../../shared/form.js?v=1';

export const meta = { code: 'S01', name: 'Sign in', side: 'main', bare: true, roles: ['asha'] };

export function render({ user }) {
  return `${pageHead('Sign in')}
    <div class="card">
      <p>Sign in to see and change only your own expenses.</p>
      <button class="btn" data-not-defined="The sign-in method (email and password, Google, another provider) is not defined. REQ-275 open question.">Sign-in method: not defined</button>
      ${button(`Sign in as ${esc(user.name)}`, { primary: true, action: 'sign-in', goto: 'S02' })}
      <p class="note"><a href="#" class="link" data-not-defined="How a new user gets an account (self sign-up, invitation) is not defined. REQ-275 open question.">New here? Get an account</a></p>
    </div>`;
}
