// Scaffold-owned glue file (STORY-105). Modules register at the markers below; do not edit the marked lines by hand.
// knm:imports
import { EntryBox } from '../entries/EntryBox'; // app route (WI-029), not a module

export const router = [
  // knm:entries
  // knm:entries-end
  // At /entries, not /: react-vite's contract tests expect / to stay the not-found page (user decision, WI-029).
  { id: 'entries', path: '/entries', element: <EntryBox /> },
];
