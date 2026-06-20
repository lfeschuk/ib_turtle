import { createWorker } from 'tesseract.js';
import * as path from 'path';
import * as fs from 'fs';

const langPath = '/Users/lfesch/work_files/chess';
const outDir = '/Users/lfesch/work_files/chess/scratch';

async function ocrPage(pageNum: number) {
  const imagePath = path.join(outDir, `page_${pageNum}.png`);
  if (!fs.existsSync(imagePath)) {
    console.error(`Image ${imagePath} does not exist.`);
    return;
  }
  
  console.log(`Starting OCR for ${imagePath}...`);
  const worker = await createWorker('eng', 1, {
    langPath: langPath,
    cachePath: langPath,
  });
  
  try {
    const { data: { text } } = await worker.recognize(imagePath);
    const outPath = path.join(outDir, `ocr_page_${pageNum}.txt`);
    fs.writeFileSync(outPath, text);
    console.log(`Saved OCR result to ${outPath}`);
  } catch (err) {
    console.error(`Error OCRing page ${pageNum}:`, err);
  } finally {
    await worker.terminate();
  }
}

async function run() {
  // OCR PDF pages 96 to 100
  for (let p = 96; p <= 100; p++) {
    await ocrPage(p);
  }
}

run();
