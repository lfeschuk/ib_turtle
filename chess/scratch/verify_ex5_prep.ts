import { Chess } from 'chess.js';

const chess = new Chess();
const prepMoves = [
  'd4', 'Nf6', 'c4', 'g6', 'Nc3', 'Bg7', 'e4', 'd6', 'f3', 'O-O',
  'Bg5', 'c5', 'd5', 'e6', 'Qd2', 'exd5', 'Nxd5', 'Be6', 'Ne2', 'Nc6',
  'Nec3', 'Bxd5', 'Nxd5', 'h6'
];

console.log("Applying prep moves for Exercise 5...");
for (const move of prepMoves) {
  try {
    const result = chess.move(move);
    if (!result) {
      console.error(`Failed to apply move: ${move}`);
      process.exit(1);
    }
  } catch (e: any) {
    console.error(`Error applying move ${move}: ${e.message}`);
    process.exit(1);
  }
}

console.log("Prep moves applied successfully!");
console.log("FEN after prep moves:", chess.fen());
console.log("Board state:");
console.log(chess.ascii());

// Test 13 Bxh6
console.log("Testing 13 Bxh6...");
try {
  const result = chess.move('Bxh6');
  if (result) {
    console.log("13 Bxh6 is legal!");
    console.log("FEN after 13 Bxh6:", chess.fen());
  } else {
    console.error("13 Bxh6 is illegal!");
  }
} catch (e: any) {
  console.error("Error testing 13 Bxh6:", e.message);
}
