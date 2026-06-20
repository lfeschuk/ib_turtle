import { Chess } from 'chess.js';

const chess = new Chess();
// Position before move 13 in Game 37
chess.load('r2q1rk1/pp3pb1/2np1npp/2pN2B1/2P1P3/5P2/PP1Q2PP/R3KB1R w KQ - 0 13');

console.log("Initial state:\n" + chess.ascii());

try {
  console.log("Playing 13. Bxh6...");
  chess.move('Bxh6');
  console.log("FEN: " + chess.fen());

  console.log("Playing 13... Nxd5...");
  chess.move('Nxd5');
  console.log("FEN: " + chess.fen());

  console.log("Playing 14. exd5...");
  chess.move('exd5'); // Assuming White recaptures with pawn
  console.log("FEN: " + chess.fen());

  console.log("Playing 14... Qh4+...");
  chess.move('Qh4+');
  console.log("FEN: " + chess.fen());

  console.log("Playing 15. g3...");
  chess.move('g3');
  console.log("FEN: " + chess.fen());

  console.log("Playing 15... Qxh6...");
  chess.move('Qxh6');
  console.log("FEN: " + chess.fen());

  console.log("Playing 16. Qxh6...");
  chess.move('Qxh6');
  console.log("FEN: " + chess.fen());

  console.log("Playing 16... Bxh6...");
  chess.move('Bxh6');
  console.log("FEN: " + chess.fen());

  console.log("Success! The sequence is legal.");
} catch (e: any) {
  console.error("Failed:", e.message);
  console.log("Current board:\n" + chess.ascii());
}
