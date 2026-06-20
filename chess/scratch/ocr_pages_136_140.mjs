import Tesseract from 'tesseract.js';
import fs from 'fs';
import path from 'path';

const pages = [136, 137, 138, 139, 140];
const scratchDir = '/Users/lfesch/work_files/chess/scratch';

async function runOCR() {
  let combinedText = '';
  for (const page of pages) {
    const imgPath = path.join(scratchDir, `page_${page}.png`);
    const txtPath = path.join(scratchDir, `page_${page}_ocr.txt`);
    
    console.log(`Starting OCR on page ${page}...`);
    try {
      const { data: { text } } = await Tesseract.recognize(imgPath, 'eng');
      fs.writeFileSync(txtPath, text, 'utf-8');
      console.log(`Finished page ${page}. Saved to ${txtPath}`);
      
      combinedText += `--- PHYSICAL PAGE ${page} ---\n${text}\n\n`;
    } catch (err) {
      console.error(`Error on page ${page}:`, err);
      combinedText += `--- PHYSICAL PAGE ${page} ---\n[OCR Error: ${err.message}]\n\n`;
    }
  }
  
  fs.writeFileSync(path.join(scratchDir, 'extracted_text_136_140.txt'), combinedText, 'utf-8');
  console.log(`All OCR text saved to scratch/extracted_text_136_140.txt`);
}

runOCR();
