/** @jest-environment node */
describe('vite config contract', () => {
  it('uses the React plugin, a dev port from PORT (default 5173) and builds to dist with source maps', async () => {
    delete process.env.PORT;
    const cfg = (await import('../../../../vite.config')).default as any;
    expect(cfg.plugins.flat(5).some((p: any) => p && /react/i.test(p.name))).toBe(true);
    expect(cfg.server.port).toBe(5173);
    expect(cfg.build).toEqual({ outDir: 'dist', sourcemap: true });
  });
  it('honours PORT', async () => {
    jest.resetModules(); process.env.PORT = '4321';
    expect(((await import('../../../../vite.config')).default as any).server.port).toBe(4321);
    delete process.env.PORT;
  });
  it('has no proxy unless API_PROXY_TARGET is set; then it proxies /api to it with the prefix removed', async () => {
    jest.resetModules(); delete process.env.API_PROXY_TARGET;
    expect(((await import('../../../../vite.config')).default as any).server.proxy).toBeUndefined();
    jest.resetModules(); process.env.API_PROXY_TARGET = 'http://127.0.0.1:8000';
    const proxy = ((await import('../../../../vite.config')).default as any).server.proxy['/api'];
    expect(proxy.target).toBe('http://127.0.0.1:8000');
    expect(proxy.rewrite('/api/users/1')).toBe('/users/1');
    delete process.env.API_PROXY_TARGET;
  });
});
