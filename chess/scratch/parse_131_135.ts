import { GoogleGenAI, Type } from "@google/genai";
import * as fs from "fs";
import * as dotenv from "dotenv";

dotenv.config({ path: '.env.local' });

const apiKey = process.env.GEMINI_API_KEY;
if (!apiKey) {
  console.error("GEMINI_API_KEY is not set in .env.local");
  process.exit(1);
}

const ai = new GoogleGenAI({ apiKey });

async function run() {
  const pdfPath = "/Users/lfesch/work_files/chess/scratch/pages_131_135.pdf";
  if (!fs.existsSync(pdfPath)) {
    console.error("PDF file not found:", pdfPath);
    process.exit(1);
  }
  const pdfBuffer = fs.readFileSync(pdfPath);
  const base64Pdf = pdfBuffer.toString("base64");

  const promptInstructions = `You are an expert chess data parser specializing in books.
Your job is to read chess book content from the pages of an uploaded PDF document containing MULTIPLE games, game fragments, theoretical variations, or exercises.

CRITICAL: Do NOT skip "Introductions", "Theoretical Variations", opening study analysis sections, or numbered Diagram captions (like Diagram 1, Diagram 2, etc.) that occur before or between illustrative games! 
In chess books, the pages contain opening variation study lines (e.g. "6...e5!", "6...Nbd7", "White plays 7 dxe5", etc.). The user wants these variations and diagrams parsed into structured, fully-interactive study positions with the same care as standard games!

Therefore, you must split this document into individual logical pieces (each represents a game, a theoretical option, or a diagram section) and output them in the requested JSON structure.
For each piece:
- Give it a clear descriptive title (e.g., "Theory: The Classical Variation (Diagram 1)", "Variation Option: 6...Nbd7", or "Game 1: Salgado vs Gallagher").
- Analyze the main line moves and their descriptions. 
- Track down main analyzed lines, comments of moves, and alternative lines mentioned in parenthetical comments (sidelines).
- Find precursor initial moves (initial_moves) leading up to the diagrammed variation.
- Output raw JSON conforming to the schema.`;

  const responseSchema = {
    type: Type.OBJECT,
    properties: {
      book_title: { type: Type.STRING, description: "A clean, descriptive title for the book compiled from text content, e.g., Starting Out: The King's Indian" },
      exercises: {
        type: Type.ARRAY,
        description: "List of individual chess exercises or game fragments extracted from the book text",
        items: {
          type: Type.OBJECT,
          properties: {
            id: { type: Type.STRING, description: "A unique slug ID, e.g. game_50" },
            title: { type: Type.STRING, description: "A clear heading/title for this game or exercise, e.g. Game 50: Ye Rongguang vs. Watson" },
            description: { type: Type.STRING, description: "Brief description of the tactical theme or context of this exercise" },
            textContext: { type: Type.STRING, description: "The segment of book text corresponding to this exercise (including the page numbers, e.g. Pages 130-131)" },
            preparsedJson: {
              type: Type.OBJECT,
              properties: {
                game_id: { type: Type.STRING, description: "A unique key representing the game within the book" },
                white: { type: Type.STRING, description: "White player's name" },
                black: { type: Type.STRING, description: "Black player's name" },
                event: { type: Type.STRING, description: "Event name of the game if any" },
                initial_moves: { type: Type.STRING, description: "Standard precursor moves played before the interactive commentary starts, separated by spaces" },
                interactive_section: {
                  type: Type.OBJECT,
                  properties: {
                    starting_move: { type: Type.INTEGER, description: "Move number where interactive commentary starts" },
                    moves: {
                      type: Type.ARRAY,
                      description: "Chronological sequence of commentaries and moves starting from starting_move",
                      items: {
                        type: Type.OBJECT,
                        properties: {
                          move_number: { type: Type.INTEGER },
                          player: { type: Type.STRING, description: "'W' or 'B'" },
                          move: { type: Type.STRING, description: "SAN of the move" },
                          commentary: { type: Type.STRING, description: "Comments on this move" }
                        },
                        required: ["move_number", "player", "move", "commentary"]
                      }
                    }
                  },
                  required: ["starting_move", "moves"]
                },
                sidelines: {
                  type: Type.ARRAY,
                  description: "Clickable sideline variations mentioned in parentheses",
                  items: {
                    type: Type.OBJECT,
                    properties: {
                      id: { type: Type.STRING },
                      name: { type: Type.STRING },
                      description: { type: Type.STRING },
                      startingMoveIndex: { type: Type.INTEGER, description: "Move index in main game moves where sideline starts (-1 means from the very start)" },
                      moves: {
                        type: Type.ARRAY,
                        items: {
                          type: Type.OBJECT,
                          properties: {
                            move_number: { type: Type.INTEGER },
                            player: { type: Type.STRING },
                            move: { type: Type.STRING },
                            commentary: { type: Type.STRING }
                          },
                          required: ["move_number", "player", "move", "commentary"]
                        }
                      }
                    },
                    required: ["id", "name", "description", "startingMoveIndex", "moves"]
                  }
                }
              },
              required: ["interactive_section"]
            }
          },
          required: ["id", "title", "description", "preparsedJson", "textContext"]
        }
      }
    },
    required: ["book_title", "exercises"]
  };

  try {
    console.log("Calling Gemini API...");
    const response = await ai.models.generateContent({
      model: "gemini-2.5-pro",
      contents: [
        {
          inlineData: {
            mimeType: "application/pdf",
            data: base64Pdf
          }
        },
        { text: "Parse this PDF content and extract all analytical variations, introduction theory, game fragments, diagrams, and illustrative games as structured JSON conforming to the requested schema. This PDF contains pages 131 to 135 of the book (corresponding to pages 130 to 134 in the printed book text). Please parse all pages in this document." }
      ],
      config: {
        systemInstruction: promptInstructions,
        responseMimeType: "application/json",
        responseSchema,
        temperature: 0.1,
      }
    });

    const outputText = response.text;
    if (!outputText) {
      throw new Error("Gemini returned empty text.");
    }

    const outputPath = "/Users/lfesch/work_files/chess/parsed_pages_131_135.json";
    fs.writeFileSync(outputPath, outputText.trim());
    console.log("JSON written to", outputPath);
  } catch (error) {
    console.error("Error calling Gemini:", error);
  }
}

run();
