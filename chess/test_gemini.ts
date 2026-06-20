import { GoogleGenAI } from "@google/genai";
import * as dotenv from "dotenv";
dotenv.config({ path: '.env.local' });

const ai = new GoogleGenAI({
  apiKey: process.env.GEMINI_API_KEY,
  httpOptions: {
    headers: {
      'User-Agent': 'aistudio-build',
    }
  }
});

async function run() {
  try {
    const response = await ai.models.generateContent({
      model: "gemini-3.5-flash",
      contents: "Respond with the word 'SUCCESS' if you can read this.",
    });
    console.log("Gemini API key works! Response:", response.text?.trim());
  } catch (err: any) {
    console.error("Gemini API error:", err);
  }
}

run();
