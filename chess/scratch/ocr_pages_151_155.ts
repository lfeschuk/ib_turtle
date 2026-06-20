import { createWorker } from 'tesseract.js';
import * as path from 'path';
import * as fs from 'fs';

const langPath = '/Users/lfesch/work_files/chess';
const outDir = '/Users/lfesch/work_files/chess/scratch';

async function ocrPage(pageNum: number) {
  const imagePath = path.join(outDir, `page_${pageNum}.png`);
  if (!fs.existsSync(imagePath)) {
    console.error(`Image ${imagePath} does not exist.`);
    return '';
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
    return text;
  } catch (err) {
    console.error(`Error OCRing page ${pageNum}:`, err);
    return '';
  } finally {
    await worker.terminate();
  }
}

async function run() {
  let combinedText = '';
  for (let p = 151; p <= 155; p++) {
    const text = await ocrPage(p);
    combinedText += `--- PDF PAGE ${p} ---\n${text}\n\n`;
  }
  const combinedPath = path.join(outDir, 'extracted_text_151_155.txt');
  fs.writeFileSync(combinedPath, combinedText);
  console.log(`Saved combined OCR text to ${combinedPath}`);
}

run();
