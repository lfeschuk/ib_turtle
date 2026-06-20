import { Chess } from 'chess.js';

function testMoves(movesStr: string) {
  const chess = new Chess();
  const moves = movesStr.trim().split(/\s+/).filter(Boolean);
  
  for (let i = 0; i < moves.length; i++) {
    const move = moves[i];
    if (/^\d+\.?$/.test(move)) continue; // skip numbers
    
    const cleanMove = move.replace(/[!?]+$/, '');
    try {
      const result = chess.move(cleanMove);
      if (!result) {
        return { ok: false, error: `Invalid move: ${move} (cleaned: ${cleanMove})` };
      }
    } catch (err: any) {
      return { ok: false, error: `Error at move ${move}: ${err.message || err}` };
    }
  }
  return { ok: true, fen: chess.fen() };
}

const baseMoves = "1 d4 Nf6 2 c4 g6 3 Nc3 Bg7 4 e4 d6 5 f3 O-O 6 Be3 e5 7 Nge2 c6 8 Qd2 Nbd7 9 O-O-O a6 10 Kb1 b5 11 c5";

// Sideline 11...dxc5
console.log("Sideline 11...dxc5:", testMoves(baseMoves + " dxc5 12 dxe5"));

// Sideline 11...exd4
console.log("Sideline 11...exd4:", testMoves(baseMoves + " exd4 12 Nxd4 dxc5 13 Nxc6"));
