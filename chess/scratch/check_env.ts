import * as dotenv from 'dotenv';
dotenv.config({ path: '.env.local' });

console.log("GEMINI_API_KEY defined:", process.env.GEMINI_API_KEY !== undefined);
if (process.env.GEMINI_API_KEY) {
  console.log("GEMINI_API_KEY length:", process.env.GEMINI_API_KEY.length);
  console.log("GEMINI_API_KEY starts with:", process.env.GEMINI_API_KEY.substring(0, 5));
} else {
  console.log("GEMINI_API_KEY is empty or falsy");
}
