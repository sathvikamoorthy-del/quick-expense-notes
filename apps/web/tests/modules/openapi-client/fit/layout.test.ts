/** @jest-environment node */
// Fit test: runs inside the app (tests/modules/openapi-client/fit); the app root is four folders up.
import fs from 'fs';
import path from 'path';

const APP = path.resolve(__dirname, '../../../..');

it('the client imports the generated schema and the generator script sits next to src', () => {
  expect(fs.readFileSync(path.join(APP, 'src/api/client.ts'), 'utf8')).toMatch(/from '\.\/schema'/);
  expect(fs.existsSync(path.join(APP, 'src/api/schema.d.ts'))).toBe(true);
  expect(fs.existsSync(path.join(APP, 'scripts/generate-client.cjs'))).toBe(true);
});
