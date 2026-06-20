import express, { Request, Response } from "express";
import path from "path";
import { createServer as createViteServer } from "vite";
import { GoogleGenAI, Type, GenerateContentResponse } from "@google/genai";
import dotenv from "dotenv";

dotenv.config();

const app = express();
const PORT = 3000;

// Setup JSON parsing with size limit for base64 images
app.use(express.json({ limit: "50mb" }));
app.use(express.urlencoded({ limit: "50mb", extended: true }));

// Initialize Gemini SDK lazily to prevent crash on startup if key is missing
let aiClient: GoogleGenAI | null = null;
function getGeminiClient(): GoogleGenAI {
  if (!aiClient) {
    const apiKey = process.env.GEMINI_API_KEY;
    if (!apiKey) {
      throw new Error("GEMINI_API_KEY environment variable is not set. Please set it in the Secrets panel.");
    }
    aiClient = new GoogleGenAI({
      apiKey,
      httpOptions: {
        headers: {
          "User-Agent": "aistudio-build",
        },
      },
    });
  }
  return aiClient;
}

// REST API for parsing chess book page or text
app.post("/api/parse-chess", async (req: Request, res: Response) => {
  try {
    const { text, image, pdfPage, customPrompt } = req.body;

    const ai = getGeminiClient();

    // Visual page or pasted text instructions
    const promptInstructions = customPrompt || `You are an expert chess data parser. Your job is to take text or images from chess books and convert them into a structured JSON format.
Separated by moves, you must identify:
- The game's meta details (White, Black, Event, Date, etc.)
- The initial moves string (moves played before the primary interactive commentary section, e.g. "1 d4 Nf6 2 c4 g6 ...")
- The starting move number of the interactive commentary section
- List of moves in the interactive commentary section. For each move, identify:
  1. The move number
  2. The player who made it ("W" or "B")
  3. The move itself in Standard Algebraic Notation (SAN)
  4. The author's commentary for that move
  5. Any alternative variations mentioned in parentheses, preserving their nested structure.

Output only raw JSON.`;

    // Multi-part content
    const contents: any[] = [];
    
    if (image) {
      // Expect base64 data string like "data:image/jpeg;base64,..." or raw base64
      let mimeType = "image/jpeg";
      let base64Data = image;
      
      const matches = image.match(/^data:([a-zA-Z0-9]+\/[a-zA-Z0-9-.+]+);base64,(.+)$/);
      if (matches && matches.length === 3) {
        mimeType = matches[1];
        base64Data = matches[2];
      }
      
      contents.push({
        inlineData: {
          mimeType,
          data: base64Data
        }
      });

      if (mimeType === "application/pdf" && pdfPage) {
        contents.push({ text: `The user specified that the chess puzzle, game fragment, or diagram to parse is specifically on Page ${pdfPage} of this PDF. Please analyze and parse ONLY Page ${pdfPage} of this uploaded document, and extract its chess moves/diagram notation.` });
      }
    }

    // Add text parts
    if (text) {
      contents.push({ text: `Analyze the following chess book content:\n\n${text}` });
    } else if (!image) {
      return res.status(400).json({ error: "No chess book text or image provided." });
    }

    contents.push({ text: `Parse this page exactly. Render the output matching the requested JSON format.` });

    // Precise response schema definition for reliable extraction
    const responseSchema = {
      type: Type.OBJECT,
      properties: {
        game_id: { type: Type.STRING, description: "A safe unique key representing the game, e.g., game_2" },
        white: { type: Type.STRING, description: "Name of the first player (White), e.g., Acebal" },
        black: { type: Type.STRING, description: "Name of the second player (Black), e.g., Gallagher" },
        event: { type: Type.STRING, description: "The event name, location and year, e.g., Candas 1992" },
        initial_moves: { type: Type.STRING, description: "All precursor moves leading up to the diagram or interactive analysis, separated by spaces. E.g. 1 d4 Nf6 2 c4 g6 3 Nc3 Bg7" },
        interactive_section: {
          type: Type.OBJECT,
          properties: {
            starting_move: { type: Type.INTEGER, description: "The starting move number of the interactive analyze section, e.g. 18" },
            moves: {
              type: Type.ARRAY,
              description: "Array of moves in chronological sequence that have commentary, starting from the starting_move.",
              items: {
                type: Type.OBJECT,
                properties: {
                  move_number: { type: Type.INTEGER, description: "Move index, e.g., 18" },
                  player: { type: Type.STRING, description: "Player who played this move, 'W' or 'B'" },
                  move: { type: Type.STRING, description: "Move played in Standard Algebraic Notation, e.g. f3, exf4, Nxd3+" },
                  commentary: { type: Type.STRING, description: "The author's notes and textual commentary explaining the move." },
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
    };

    const response: GenerateContentResponse = await ai.models.generateContent({
      model: "gemini-3.5-flash",
      contents: contents.length === 1 ? contents[0] : { parts: contents },
      config: {
        systemInstruction: promptInstructions,
        responseMimeType: "application/json",
        responseSchema,
        temperature: 0.1, // low temperature for precise factual parsing
      }
    });

    const outputText = response.text;
    if (!outputText) {
      throw new Error("Gemini returned empty text.");
    }

    // Try parsing to verify it is valid JSON
    const parsedData = JSON.parse(outputText.trim());
    return res.json(parsedData);

  } catch (error: any) {
    console.error("Gemini Parsing Error:", error);
    return res.status(500).json({
      error: error.message || "Failed to parse chess book data via Gemini.",
      details: error.stack
    });
  }
});

app.post("/api/parse-book", async (req: Request, res: Response) => {
  try {
    const { text, file, customPrompt, pdfStartPage, pdfEndPage } = req.body;

    if ((!text || !text.trim()) && !file) {
      return res.status(400).json({ error: "No chess book text or uploaded file (PDF/Image) provided." });
    }

    const ai = getGeminiClient();

    const promptInstructions = customPrompt || `You are an expert chess data parser specializing in books.
Your job is to read chess book content (which may be parsed from text, images, or from the pages of an uploaded PDF document) containing MULTIPLE games, game fragments, theoretical variations, or exercises.

CRITICAL: Do NOT skip "Introductions", "Theoretical Variations", opening study analysis sections, or numbered Diagram captions (like Diagram 1, Diagram 2, etc.) that occur before or between illustrative games! 
In chess books, the pages before the first full game (such as Page 12 and 13) contain highly critical opening variation study lines (e.g. "6...e5!", "6...Nbd7", "White plays 7 dxe5", etc.). The user wants these introductory variations and diagrams parsed into structured, fully-interactive study positions with the same care as standard games!

Therefore, you must split this text/document into individual logical pieces (each represents a game, a theoretical option, or a diagram section) and output them in the requested JSON structure.
For each piece:
- Give it a clear descriptive title (e.g., "Theory: The Classical Variation (Diagram 1)", "Variation Option: 6...Nbd7", or "Game 1: Salgado vs Gallagher").
- Analyze the main line moves and their descriptions. 
- Track down main analyzed lines, comments of moves, and alternative lines mentioned in parenthetical comments.
- Find precursor initial moves (initial_moves) leading up to the diagrammed variation.
- Output raw JSON conforming to the schema.`;

    const contents: any[] = [];
    let isPdf = false;

    if (file) {
      let mimeType = "application/pdf";
      let base64Data = file;
      
      const matches = file.match(/^data:([a-zA-Z0-9]+\/[a-zA-Z0-9-.+]+);base64,(.+)$/);
      if (matches && matches.length === 3) {
        mimeType = matches[1];
        base64Data = matches[2];
      }
      
      if (mimeType === "application/pdf") {
        isPdf = true;
      }

      contents.push({
        inlineData: {
          mimeType,
          data: base64Data
        }
      });
    }

    if (text) {
      contents.push({ text: `Analyze the following companion chess text:\n\n${text}` });
    }

    let extractInstruction = `Parse this book content and extract all analytical variations, introduction theory, game fragments, diagrams, and illustrative games as structured JSON conforming to the requested schema.`;
    if (isPdf) {
      if (pdfStartPage || pdfEndPage) {
        extractInstruction += ` Note: The user specified to analyze specifically from Page ${pdfStartPage || 1} to Page ${pdfEndPage || 15} of this PDF. Please extract every distinct theory analysis, variation sequence, annotated paragraph, diagram, or game containing moves / chess notation / diagram positions found within pages ${pdfStartPage || 1} and ${pdfEndPage || 15} of this PDF, and split them logically.`;
      } else {
        extractInstruction += ` If analyzing a PDF or documents, extract up to 10 prominent exercises/positions/variations found within the pages.`;
      }
    } else {
      extractInstruction += ` extract up to 10 prominent exercises/positions/variations found within the chapters.`;
    }

    contents.push({ text: extractInstruction });

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
              id: { type: Type.STRING, description: "A unique slug ID, e.g. end_exc_1" },
              title: { type: Type.STRING, description: "A clear heading/title for this game or exercise, e.g. Game 3: Capablanca vs Lasker" },
              description: { type: Type.STRING, description: "Brief description of the tactical theme or context of this exercise" },
              textContext: { type: Type.STRING, description: "The segment of book text corresponding to this exercise" },
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

    const response: GenerateContentResponse = await ai.models.generateContent({
      model: "gemini-3.5-flash",
      contents: contents.length === 1 ? contents[0] : { parts: contents },
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

    const parsedData = JSON.parse(outputText.trim());
    return res.json(parsedData);

  } catch (error: any) {
    console.error("Gemini Parse Book Error:", error);
    return res.status(500).json({
      error: error.message || "Failed to parse chess book text via Gemini.",
      details: error.stack
    });
  }
});

// Configure Vite or Serve Production Assets
async function serveApp() {
  if (process.env.NODE_ENV !== "production") {
    const vite = await createViteServer({
      server: { middlewareMode: true },
      appType: "spa",
    });
    app.use(vite.middlewares);
  } else {
    const distPath = path.join(process.cwd(), "dist");
    app.use(express.static(distPath));
    app.get("*", (req: Request, res: Response) => {
      res.sendFile(path.join(distPath, "index.html"));
    });
  }

  app.listen(PORT, "0.0.0.0", () => {
    console.log(`Server running on port ${PORT}`);
  });
}

serveApp();
