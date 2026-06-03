import { chromium } from 'playwright';
import { resolve } from 'path';
import { existsSync } from 'fs';

const args = process.argv.slice(2);

function flag(name) {
  const i = args.indexOf(name);
  return i >= 0 ? args[i + 1] : null;
}

const inputPath = flag('--input');
const outputPath = flag('--output') ?? 'carrossel.pdf';

if (!inputPath) {
  process.stderr.write('Erro: --input é obrigatório\n');
  process.stderr.write('Uso: node carousel_studio/render.mjs --input slides.html --output saida.pdf\n');
  process.exit(1);
}

const absInput = resolve(inputPath);
if (!existsSync(absInput)) {
  process.stderr.write(`Erro: arquivo não encontrado: ${absInput}\n`);
  process.exit(1);
}

process.stderr.write('Abrindo slides...\n');
const browser = await chromium.launch();
const page = await browser.newPage();

await page.goto(`file://${absInput}`);

const slideCount = await page.locator('.slide').count();
process.stderr.write(`${slideCount} slide(s) encontrado(s)\n`);

process.stderr.write('Exportando PDF...\n');
await page.pdf({
  path: outputPath,
  width: '1080px',
  height: '1080px',
  printBackground: true,
});

await browser.close();

process.stdout.write(resolve(outputPath) + '\n');
process.stderr.write(`PDF salvo: ${outputPath}\n`);
