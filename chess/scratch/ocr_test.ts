import { createWorker } from 'tesseract.js';
import * as path from 'path';

async function run() {
  const worker = await createWorker('eng', 1, {
    cachePath: path.join(process.cwd()),
    gzip: false,
    // logger: m => console.log(m)
  });
  
  const imagePath = '/Users/lfesch/work_files/chess/scratch/page_176.png';
  console.log(`Running OCR on ${imagePath}...`);
  const { data: { text } } = await worker.recognize(imagePath);
  console.log("OCR Result:");
  console.log(text);
  await worker.terminate();
}

run().catch(err => console.error(err));
