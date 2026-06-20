import { COMPACT_68_GAMES } from './src/all68GamesData';
import { Chess } from 'chess.js';

console.log(`Starting validation of ${COMPACT_68_GAMES.length} games...`);

let okCount = 0;
const errors: any[] = [];

for (const game of COMPACT_68_GAMES) {
  const chess = new Chess();
  
  // 1. Play initial moves
  const initialMoves = game.initial.trim().split(/\s+/).filter(Boolean);
  let failed = false;
  let moveIndex = 0;
  
  for (let move of initialMoves) {
    // Skip number indicators like "10" or "15."
    if (/^\d+\.?$/.test(move)) {
      continue;
    }
    // Clean annotation suffixes from moves (e.g., "Nc4?!" -> "Nc4")
    const cleanMove = move.replace(/[!?]+$/, '');
    try {
      const result = chess.move(cleanMove);
      if (!result) {
        throw new Error(`Invalid move: ${move} (cleaned: ${cleanMove})`);
      }
      moveIndex++;
    } catch (err: any) {
      errors.push({
        num: game.num,
        white: game.white,
        black: game.black,
        stage: 'initial',
        moveIndex,
        move: `${move} (cleaned: ${cleanMove})`,
        error: err.message || err
      });
      failed = true;
      break;
    }
  }
  
  if (failed) continue;
  
  // 2. Play main moves
  let mainIndex = 0;
  for (const moveObj of game.moves) {
    const move = moveObj.m;
    // Skip number indicators if any
    if (/^\d+\.?$/.test(move)) {
      continue;
    }
    const cleanMove = move.replace(/[!?]+$/, '');
    try {
      const result = chess.move(cleanMove);
      if (!result) {
        throw new Error(`Invalid move: ${move} (cleaned: ${cleanMove})`);
      }
      mainIndex++;
    } catch (err: any) {
      errors.push({
        num: game.num,
        white: game.white,
        black: game.black,
        stage: 'interactive',
        moveIndex: mainIndex,
        move: `${move} (cleaned: ${cleanMove})`,
        error: err.message || err
      });
      failed = true;
      break;
    }
  }
  
  if (!failed) {
    okCount++;
  }
}

console.log(`Validation complete: ${okCount} / ${COMPACT_68_GAMES.length} games passed.`);
if (errors.length > 0) {
  console.error(`Found ${errors.length} errors:`);
  console.error(JSON.stringify(errors, null, 2));
  process.exit(1);
} else {
  console.log("All games in src/all68GamesData.ts have valid SAN sequences and conform to standard chess rules!");
  process.exit(0);
}
