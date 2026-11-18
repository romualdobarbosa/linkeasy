// Smoke test dos renderizadores: roda carousel_studio/render.mjs e infographic/render.mjs
// nos arquivos de examples/, num diretório temporário, e confere as saídas.
// Uso: npm run test:render (ou make render-smoke).
import { execFileSync } from 'node:child_process';
import { mkdtempSync, readFileSync, rmSync, statSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const examples = join(root, 'examples');
const tmp = mkdtempSync(join(tmpdir(), 'linkeasy-smoke-'));

let failures = 0;
function check(cond, msg) {
  console.log(`${cond ? 'ok  ' : 'FALHA'} ${msg}`);
  if (!cond) failures++;
}

function run(script, args, input) {
  execFileSync(process.execPath, [join(root, script), ...args], {
    cwd: root,
    input,
    stdio: [input === undefined ? 'ignore' : 'pipe', 'pipe', 'inherit'],
  });
}

function pdfPageCount(path) {
  // O Chromium grava os objetos de página sem compressão; /Type /Page sem o "s" final.
  const text = readFileSync(path).toString('latin1');
  return (text.match(/\/Type\s*\/Page(?![a-zA-Z])/g) ?? []).length;
}

function pngSize(path) {
  const buf = readFileSync(path);
  const signature = buf.subarray(0, 8).toString('hex');
  if (signature !== '89504e470d0a1a0a') return null;
  return { width: buf.readUInt32BE(16), height: buf.readUInt32BE(20) };
}

try {
  // Carrossel: uma página no PDF por .slide no HTML.
  const html = join(examples, 'carrossel-exemplo.html');
  const expectedPages = (readFileSync(html, 'utf-8').match(/class="slide"/g) ?? []).length;
  const pdf = join(tmp, 'carrossel.pdf');
  run('carousel_studio/render.mjs', ['--input', html, '--output', pdf]);
  check(statSync(pdf, { throwIfNoEntry: false })?.size > 0, 'carrossel: PDF gerado');
  const pages = pdfPageCount(pdf);
  check(
    expectedPages > 0 && pages === expectedPages,
    `carrossel: ${pages} página(s), esperado ${expectedPages}`,
  );

  // Infográfico: via stdin (forma usada pela skill) e via --input.
  const syntaxFile = join(examples, 'infografico-exemplo.txt');
  const pngStdin = join(tmp, 'infografico-stdin.png');
  const pngInput = join(tmp, 'infografico-input.png');
  run('infographic/render.mjs', ['--output', pngStdin], readFileSync(syntaxFile));
  run('infographic/render.mjs', ['--input', syntaxFile, '--output', pngInput]);
  for (const [label, png] of [['stdin', pngStdin], ['--input', pngInput]]) {
    const size = statSync(png, { throwIfNoEntry: false })?.size ?? 0;
    check(size > 1000, `infográfico (${label}): PNG com ${size} bytes`);
    const dims = size ? pngSize(png) : null;
    check(
      dims?.width === 1200 && dims?.height === 627,
      `infográfico (${label}): dimensões ${dims ? `${dims.width}x${dims.height}` : 'inválidas'}`,
    );
  }
} catch (err) {
  console.error(err.message);
  failures++;
} finally {
  rmSync(tmp, { recursive: true, force: true });
}

if (failures) {
  console.error(`\n${failures} verificação(ões) falharam`);
  process.exit(1);
}
console.log('\nsmoke test dos renderizadores ok');
