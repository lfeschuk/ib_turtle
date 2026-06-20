import * as fs from 'fs';
import * as path from 'path';
import http from 'http';

const pdfPath = '/Users/lfesch/work_files/chess/Starting_Out_The_Kings_Indian_Joe_z_library_sk,_1lib_sk,.pdf';
console.log(`Reading PDF from ${pdfPath}...`);
const pdfBuffer = fs.readFileSync(pdfPath);
const base64Pdf = pdfBuffer.toString('base64');
console.log(`PDF size: ${pdfBuffer.length} bytes. Base64 size: ${base64Pdf.length} chars.`);

const payload = JSON.stringify({
  file: `data:application/pdf;base64,${base64Pdf}`,
  pdfStartPage: 101,
  pdfEndPage: 105
});

console.log("Sending request to server...");
const req = http.request({
  hostname: 'localhost',
  port: 3000,
  path: '/api/parse-book',
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Content-Length': Buffer.byteLength(payload)
  }
}, (res) => {
  console.log(`Response status: ${res.statusCode}`);
  let data = '';
  res.on('data', (chunk) => {
    data += chunk;
  });
  res.on('end', () => {
    if (res.statusCode === 200) {
      console.log("Success! Writing output to parsed_pages_101_105_api.json...");
      fs.writeFileSync('parsed_pages_101_105_api.json', data);
      console.log("Done.");
    } else {
      console.error("Error response from server:");
      console.error(data);
    }
  });
});

req.on('error', (e) => {
  console.error(`Request failed: ${e.message}`);
});

req.write(payload);
req.end();
