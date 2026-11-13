// Runs before every test file: Testing Library's DOM matchers and the browser APIs jsdom does not provide.
// Test files that opt into the node environment have no window: the browser polyfills are skipped there.
// The polyfills are installed on Window.prototype so they stay available even when a test deletes the
// instance property (the module is loaded once per test file, so a re-import does not run this again).
import '@testing-library/jest-dom';

if (typeof window !== 'undefined') {
  const proto = Object.getPrototypeOf(window) as any;
  const define = (name: string, value: unknown) =>
    Object.defineProperty(proto, name, { value, writable: true, configurable: true });

  if (!window.matchMedia) {
    define('matchMedia', (query: string) => ({ matches: false, media: query, onchange: null, addListener() {}, removeListener() {}, addEventListener() {}, removeEventListener() {}, dispatchEvent: () => false }));
  }
  if (!(window as any).ResizeObserver) {
    define('ResizeObserver', class { observe() {} unobserve() {} disconnect() {} });
  }
  if (!window.scrollTo || String(window.scrollTo).includes('not implemented')) window.scrollTo = (() => undefined) as typeof window.scrollTo;
}
