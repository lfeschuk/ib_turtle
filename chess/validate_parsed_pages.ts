import * as fs from 'fs';
import { Chess } from 'chess.js';

interface Move {
  move_number: number;
  player: string;
  move: string;
  commentary?: string;
}

interface Sideline {
  id: string;
  name: string;
  description?: string;
  startingMoveIndex: number;
  moves: Move[];
}

interface Exercise {
  id: string;
  title: string;
  preparsedJson: {
    game_id: string;
    white: string;
    black: string;
    event?: string;
    initial_moves: string;
    interactive_section: {
      starting_move: number;
      moves: Move[];
    };
    sidelines?: Sideline[];
  };
}

interface ParsedFile {
  book_title: string;
  exercises: Exercise[];
}

const filePath = '/Users/lfesch/work_files/chess/parsed_pages_131_135.json';
console.log(`Loading and validating ${filePath}...`);

const fileContent = fs.readFileSync(filePath, 'utf-8');
const data: ParsedFile = JSON.parse(fileContent);

let totalErrors = 0;

function cleanMoveStr(m: string): string {
  return m.replace(/[!?+#=]+/g, '');
}

for (const ex of data.exercises) {
  const game = ex.preparsedJson;
  console.log(`\n--- Validating Game: ${ex.title} (${game.white} vs. ${game.black}) ---`);

  // 1. Play initial moves
  const chess = new Chess();
  const initialMoves = game.initial_moves.trim().split(/\s+/).filter(Boolean);
  let failedInitial = false;

  for (let i = 0; i < initialMoves.length; i++) {
    const move = initialMoves[i];
    // Skip move numbers
    if (/^\d+\.?$/.test(move)) continue;
    const cleaned = cleanMoveStr(move);
    try {
      if (!chess.move(cleaned)) {
        throw new Error(`chess.js returned null for move: ${move}`);
      }
    } catch (err: any) {
      console.error(`Error in initial moves at index ${i} (${move}):`, err.message || err);
      failedInitial = true;
      totalErrors++;
      break;
    }
  }

  if (failedInitial) {
    console.error(`Skipping remaining validation for ${ex.title} due to initial move failure.`);
    continue;
  }

  // Save the state after initial moves
  const fenAfterInitial = chess.fen();

  // 2. Play main moves
  let failedMain = false;
  const mainMoves = game.interactive_section.moves;
  for (let i = 0; i < mainMoves.length; i++) {
    const moveObj = mainMoves[i];
    const cleaned = cleanMoveStr(moveObj.move);
    try {
      if (!chess.move(cleaned)) {
        throw new Error(`chess.js returned null for move: ${moveObj.move}`);
      }
    } catch (err: any) {
      console.error(`Error in main moves at index ${i} (${moveObj.move_number}${moveObj.player}: ${moveObj.move}):`, err.message || err);
      console.log("ASCII board state before error:\n" + chess.ascii());
      failedMain = true;
      totalErrors++;
      break;
    }
  }

  if (!failedMain) {
    console.log(`Main line is VALID! FEN: ${chess.fen()}`);
  }

  // 3. Play sidelines
  if (game.sidelines && game.sidelines.length > 0) {
    for (const side of game.sidelines) {
      // Reset to starting position for the sideline
      const sideChess = new Chess();
      sideChess.load(fenAfterInitial);

      // Play main moves up to startingMoveIndex
      let failedPrep = false;
      if (side.startingMoveIndex >= 0) {
        for (let i = 0; i <= side.startingMoveIndex; i++) {
          const moveObj = mainMoves[i];
          const cleaned = cleanMoveStr(moveObj.move);
          try {
            if (!sideChess.move(cleaned)) {
              throw new Error(`chess.js returned null for prep move: ${moveObj.move}`);
            }
          } catch (err: any) {
            console.error(`Error in preparing sideline ${side.name} at main move index ${i} (${moveObj.move}):`, err.message || err);
            failedPrep = true;
            totalErrors++;
            break;
          }
        }
      }

      if (failedPrep) {
        console.error(`Skipping sideline ${side.name} due to prep failure.`);
        continue;
      }

      // Print FEN before sideline moves
      console.log(`FEN before sideline "${side.name}": ${sideChess.fen()}`);

      // Play sideline moves
      let failedSide = false;
      for (let i = 0; i < side.moves.length; i++) {
        const moveObj = side.moves[i];
        const cleaned = cleanMoveStr(moveObj.move);
        try {
          if (!sideChess.move(cleaned)) {
            throw new Error(`chess.js returned null for sideline move: ${moveObj.move}`);
          }
        } catch (err: any) {
          console.error(`Error in sideline ${side.name} at index ${i} (${moveObj.move_number}${moveObj.player}: ${moveObj.move}):`, err.message || err);
          console.log("ASCII board state before error:\n" + sideChess.ascii());
          failedSide = true;
          totalErrors++;
          break;
        }
      }

      if (!failedSide) {
        console.log(`Sideline "${side.name}" is VALID! FEN: ${sideChess.fen()}`);
      }
    }
  }
}

console.log(`\nValidation finished. Total errors found: ${totalErrors}`);
if (totalErrors > 0) {
  process.exit(1);
} else {
  console.log(`All moves in ${filePath} are VALID!`);
  process.exit(0);
}
