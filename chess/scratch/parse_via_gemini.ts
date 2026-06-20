import { GoogleGenAI, Type } from "@google/genai";
import * as fs from "fs";
import * as dotenv from "dotenv";

dotenv.config();

const apiKey = process.env.GEMINI_API_KEY;
if (!apiKey) {
  console.error("GEMINI_API_KEY is not defined in environment.");
  process.exit(1);
}

const ai = new GoogleGenAI({
  apiKey,
  httpOptions: {
    headers: {
      "User-Agent": "aistudio-build",
    },
  },
});

async function run() {
  try {
    const pdfPath = "/Users/lfesch/work_files/chess/pages_56_60.pdf";
    console.log(`Loading PDF: ${pdfPath}`);
    const pdfData = fs.readFileSync(pdfPath);
    const base64Pdf = pdfData.toString("base64");

    const contents = [
      {
        inlineData: {
          mimeType: "application/pdf",
          data: base64Pdf
        }
      },
      {
        text: "Parse this book content and extract all analytical variations, introduction theory, game fragments, diagrams, and illustrative games as structured JSON conforming to the requested schema. This PDF contains exactly pages 56 to 60 of the book. Extract every distinct game, fragment or diagram analysis found in this document."
      }
    ];

    const promptInstructions = `You are an expert chess data parser specializing in books.
Your job is to read chess book content (which may be parsed from text, images, or from the pages of an uploaded PDF document) containing MULTIPLE games, game fragments, theoretical variations, or exercises.

CRITICAL: Do NOT skip "Introductions", "Theoretical Variations", opening study analysis sections, or numbered Diagram captions (like Diagram 1, Diagram 2, etc.) that occur before or between illustrative games! 

Therefore, you must split this text/document into individual logical pieces (each represents a game, a theoretical option, or a diagram section) and output them in the requested JSON structure.
For each piece:
- Give it a clear descriptive title (e.g., "Theory: The Classical Variation (Diagram 1)", "Variation Option: 6...Nbd7", or "Game 17: Koutsin vs. Frolov").
- Analyze the main line moves and their descriptions. 
- Track down main analyzed lines, comments of moves, and alternative lines mentioned in parenthetical comments.
- Find precursor initial moves (initial_moves) leading up to the diagrammed variation.
- Output raw JSON conforming to the schema.`;

    const responseSchema = {
      type: Type.OBJECT,
      properties: {
        book_title: { type: Type.STRING, description: "A clean, descriptive title for the book compiled from text content, e.g., Common Endgames" },
        exercises: {
          type: Type.ARRAY,
          description: "List of individual chess exercises or game fragments extracted from the book text",
          items: {
            type: Type.OBJECT,
            properties: {
              id: { type: Type.STRING, description: "A unique slug ID, e.g. game_17" },
              title: { type: Type.STRING, description: "A clear heading/title for this game or exercise, e.g. Game 17: Koutsin vs. Frolov" },
              description: { type: Type.STRING, description: "Brief description of the tactical theme or context of this exercise" },
              textContext: { type: Type.STRING, description: "The segment of book text corresponding to this exercise (e.g. Page 56)" },
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

    console.log("Calling Gemini API...");
    const response = await ai.models.generateContent({
      model: "gemini-2.5-pro", // use pro for better structured parsing of pdfs
      contents: { parts: contents },
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

    console.log("Gemini API call finished. Saving output to parsed_pages_56_60.json...");
    fs.writeFileSync("/Users/lfesch/work_files/chess/parsed_pages_56_60.json", outputText.trim());
    console.log("Done!");

  } catch (err: any) {
    console.error("Error during parsing:", err.message || err);
    if (err.stack) console.error(err.stack);
    process.exit(1);
  }
}

run();
