// knm-managed: v1 version: 1
// Approved screen modules. Add a line here when a screen is added: CODE: './screens/<side>/<name>.js?v=1'
export const SCREENS = {
  S01: './screens/main/sign-in.js?v=1',
  S02: './screens/main/entry-box.js?v=1',
  S03: './screens/main/saved-entries.js?v=1',
  S04: './screens/main/edit-entry.js?v=1',
  S05: './screens/main/monthly-summary.js?v=1'
};

export async function loadScreen(code) {
  const path = SCREENS[code];
  if (!path) throw new Error(`Unknown screen code: ${code}`);
  return import(path);
}
