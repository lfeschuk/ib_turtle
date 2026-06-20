import { Chess } from 'chess.js';

const moves = [
  "Nf3", "Nf6", "c4", "g6", "d4", "Bg7", "Nc3", "O-O", "g3", "d6", 
  "Bg2", "Nbd7", "O-O", "e5", "e4", "c6", "h3", "Qb6",
  "c5", "dxc5", "dxe5", "Ne8", "e6", "fxe6", "Ng5", "Ne5",
  "f4", "Nf7", "Nxf7", "Bd4+", "Kh2", "Rxf7", "e5", "Nc7", "Ne4", "Nd5", "h4",
  "Qd8", "h5", "Rg7", "Ng5", "gxh5", "Qxh5", "Qe7", "Be4", "Bd7", "Qh3",
  "c4", "Rb1", "b5", "Kg2", "c5", "f5"
];

const chess = new Chess();
for (const m of moves) {
  chess.move(m);
}

console.log("Legal moves for Black after 27.f5:");
console.log(chess.moves().join(", "));
