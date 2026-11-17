// Scaffold-owned glue file (STORY-105). Modules register at the markers below; do not edit the marked lines by hand.
// knm:imports
import { EntryBox } from '../entries/EntryBox'; // app route (WI-029), not a module
import { RequireAuth } from '../auth/RequireAuth'; // app route guard (WI-039), not a module
import { SignIn } from '../auth/SignIn'; // app route (WI-039), not a module

export const router = [
  // knm:entries
  // knm:entries-end
  // At /entries, not /: react-vite's contract tests expect / to stay the not-found page (user decision, WI-029).
  { id: 'sign-in', path: '/sign-in', element: <SignIn /> },
  { id: 'entries', path: '/entries', element: <RequireAuth><EntryBox /></RequireAuth> },
];
