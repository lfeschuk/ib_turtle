import { createWorker } from 'tesseract.js';
import * as path from 'path';
import * as fs from 'fs';

async function run() {
  const worker = await createWorker('eng', 1, {
    cachePath: path.join(process.cwd()),
    gzip: false,
  });
  
  for (const pageNum of [173, 174]) {
    const imagePath = `/Users/lfesch/work_files/chess/scratch/page_${pageNum}.png`;
    console.log(`Running OCR on ${imagePath}...`);
    const { data: { text } } = await worker.recognize(imagePath);
    const outputPath = `/Users/lfesch/work_files/chess/scratch/page_${pageNum}_text.txt`;
    fs.writeFileSync(outputPath, text);
    console.log(`Saved OCR result to ${outputPath}`);
  }
  await worker.terminate();
}

run().catch(err => console.error(err));
