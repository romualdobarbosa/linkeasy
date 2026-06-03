import { renderToString } from '@antv/infographic/ssr';
import { chromium } from 'playwright';
import { writeFileSync } from 'fs';
import { resolve } from 'path';

const args = process.argv.slice(2);

function flag(name) {
  const i = args.indexOf(name);
  return i >= 0 ? args[i + 1] : null;
}

const outputPath = flag('--output') ?? 'output.png';
const svgPath = flag('--svg') ?? null;
const width = parseInt(flag('--width') ?? '1200');
const height = parseInt(flag('--height') ?? '627');

const chunks = [];
for await (const chunk of process.stdin) chunks.push(chunk);
const syntax = Buffer.concat(chunks).toString('utf-8').trim();

if (!syntax) {
  process.stderr.write('Error: nenhuma sintaxe recebida via stdin\n');
  process.exit(1);
}

process.stderr.write('Renderizando SVG...\n');
const svg = await renderToString(syntax, { width, height });

if (svgPath) {
  writeFileSync(svgPath, svg, 'utf-8');
  process.stderr.write(`SVG salvo: ${svgPath}\n`);
}

// Extrair dimensões reais do SVG gerado para escalar ao canvas
const svgWidthMatch = svg.match(/<svg[^>]*\swidth="(\d+(?:\.\d+)?)"/);
const svgHeightMatch = svg.match(/<svg[^>]*\sheight="(\d+(?:\.\d+)?)"/);
const svgW = svgWidthMatch ? parseFloat(svgWidthMatch[1]) : width;
const svgH = svgHeightMatch ? parseFloat(svgHeightMatch[1]) : height;

const padding = 40;
const availW = width - padding * 2;
const availH = height - padding * 2;
const scale = Math.min(availW / svgW, availH / svgH);

// Remover declarações XML antes de embedar no HTML
const svgBody = svg.replace(/^(<\?xml[^?]*\?>|<\?xml-stylesheet[^?]*\?>|\s)+/g, '').trim();

const html = `<!DOCTYPE html>
<html>
<head>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body { width: ${width}px; height: ${height}px; background: white; overflow: hidden;
         display: flex; align-items: center; justify-content: center; }
  .wrap { transform: scale(${scale}); transform-origin: center center; line-height: 0; }
</style>
</head>
<body><div class="wrap">${svgBody}</div></body>
</html>`;

process.stderr.write('Exportando PNG...\n');
const browser = await chromium.launch();
const page = await browser.newPage();
await page.setViewportSize({ width, height });
await page.setContent(html);
await page.screenshot({ path: outputPath });
await browser.close();

process.stdout.write(resolve(outputPath) + '\n');
process.stderr.write(`PNG salvo: ${outputPath}\n`);
