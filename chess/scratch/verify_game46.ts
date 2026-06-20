import { Chess } from 'chess.js';

const chess = new Chess();
const moves = [
  'd4', 'Nf6', 'c4', 'g6', 'Nf3', 'Bg7', 'g3', 'O-O', 'Bg2', 'd6',
  'O-O', 'Nc6', 'Nc3', 'a6', 'h3', 'Rb8', 'e4', 'b5', 'e5', 'Nd7',
  'cxb5', 'axb5', 'Ng5', 'dxe5', 'Bxc6', 'exd4', 'Nxb5', 'Rb6'
];

console.log("Playing initial moves...");
for (const move of moves) {
  const result = chess.move(move);
  if (!result) {
    console.error(`Failed on move: ${move}`);
    process.exit(1);
  }
}

console.log("Position after 14...Rb6:");
console.log(chess.ascii());
console.log("FEN:", chess.fen());

// Let's list legal moves
console.log("Legal moves in this position:");
console.log(chess.moves().join(', '));

// Try White 15. Nxb6
{
  const testChess = new Chess(chess.fen());
  try {
    testChess.move('Nxb6');
    console.log("\nAfter 15. Nxb6, legal moves for Black:");
    console.log(testChess.moves().join(', '));
    
    // Test Black 15...Nxb6
    const testChess2 = new Chess(testChess.fen());
    testChess2.move('Nxb6');
    console.log("After 15. Nxb6 Nxb6, legal moves for White:");
    console.log(testChess2.moves().join(', '));
  } catch (e) {
    console.log("15. Nxb6 failed:", e);
  }
}

// Try White 15. Bxd7
{
  const testChess = new Chess(chess.fen());
  try {
    testChess.move('Bxd7');
    console.log("\nAfter 15. Bxd7, legal moves for Black:");
    console.log(testChess.moves().join(', '));
  } catch (e) {
    console.log("15. Bxd7 failed:", e);
  }
}
