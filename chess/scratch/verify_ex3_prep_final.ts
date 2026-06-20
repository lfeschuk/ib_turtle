import { Chess } from 'chess.js';

const chess = new Chess();
const prepMoves = [
  'd4', 'Nf6', 'c4', 'g6', 'Nc3', 'Bg7', 'e4', 'd6', 'Nf3', 'O-O',
  'Be2', 'e5', 'O-O', 'Nc6', 'd5', 'Ne7', 'Ne1', 'Nd7', 'Be3', 'f5',
  'f3', 'f4', 'Bf2', 'g5', 'Rc1', 'Rf6', 'Nd3', 'Rh6', 'b4', 'Qe8',
  'Kh1', 'Qh5', 'Bg1', 'Nf6', 'Nb5'
];

console.log("Applying prep moves...");
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

// Test 18...Qh4!!
console.log("Testing 18...Qh4...");
try {
  const result = chess.move('Qh4');
  if (result) {
    console.log("18...Qh4 is legal!");
    console.log("FEN after 18...Qh4:", chess.fen());
  } else {
    console.error("18...Qh4 is illegal!");
  }
} catch (e: any) {
  console.error("Error testing 18...Qh4:", e.message);
}
