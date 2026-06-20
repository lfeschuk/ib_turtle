import { Chess } from 'chess.js';

const chess = new Chess();
const moves = [
  "d4", "Nf6", "c4", "g6", "Nc3", "Bg7", "e4", "d6", "f3", "O-O", 
  "Be3", "e5", "Nge2", "c6", "Qd2", "Nbd7", "O-O-O", "a6", "Kb1", "b5", 
  "c5", "b4", "Na4", "d5", "dxe5", "Nxe5", "Nb6", "Rb8", "Ng3", "Be6", 
  "Bd4", "Qc7", "f4", "Ned7", "e5", "Ne4", "Nxe4", "Bf5", "Bd3", "dxe4",
  "Bc2", "Rfe8", "h3", "Bf8", "g4", "Nxc5", "gxf5", "Rxb6", "fxg6", "hxg6",
  "Qe3", "Nd7", "Bxb6", "Nxb6", "Qxe4", "c5", "h4"
];

console.log("Playing moves...");
for (const m of moves) {
  try {
    chess.move(m);
    console.log(`Played ${m}, FEN: ${chess.fen()}`);
  } catch (err: any) {
    console.error(`Error playing ${m}:`, err.message);
    console.log("ASCII board:\n" + chess.ascii());
    process.exit(1);
  }
}

console.log("Board state after 20. Bd3:");
console.log("ASCII board:\n" + chess.ascii());
console.log("Whose turn is it?", chess.turn() === 'w' ? "White" : "Black");
console.log("Legal moves for Black:", chess.moves());


