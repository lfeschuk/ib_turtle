import { Chess } from 'chess.js';

const chess = new Chess();
const moves = [
  "d4", "Nf6", "c4", "g6", "Nc3", "Bg7", "e4", "d6", "f3", "O-O",
  "Bg5", "c5", "d5", "e6", "Qd2", "exd5", "Nxd5", "Be6", "Ne2", "Nc6",
  "Nec3", "Bxd5", "Nxd5", "h6", "Nxf6+", "Bxf6", "Bxh6", "Bxb2", "Rb1", "Bc3",
  "Qxc3", "Qh4+", "g3", "Qxh6", "Qd2", "Qh5", "Bg2", "Nd4", "O-O", "b6",
  "f4", "Rae8", "Rbe1", "Kg7", "h3", "f6", "a4", "Re7", "a5", "bxa5",
  "Qxa5", "Nc2", "g4", "Qh8", "Re2", "Nd4", "Ref2", "Qh4", "Qa6", "Rd7",
  "e5", "fxe5", "fxe5", "Rxf2", "Rxf2", "dxe5", "Qc8", "Qe7", "Bd5",
  "Rd8", "Qa6", "Rf8", "Rxf8", "Qxf8", "Qxa7+", "Kh6", "Kg2", "Ne2",
  "h4", "Nf4+", "Kg3", "Ne2+", "Kg2", "Nf4+", "Kg3", "Ne2+"
];

console.log("Playing Game 37 moves...");
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

console.log("Game 37 is VALID!");
console.log("Final FEN:", chess.fen());
