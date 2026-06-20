import { Chess } from 'chess.js';

const chess = new Chess();

const moves = [
  "Nf3", "Nf6", "c4", "g6", "d4", "Bg7", "Nc3", "O-O", "g3", "d6", 
  "Bg2", "Nbd7", "O-O", "e5", "e4", "a6", "h3", "b5",
  "cxb5", "axb5", "b4", "c5"
];

for (const m of moves) {
  chess.move(m);
}

// Sideline: 12 dxe5 dxe5 13 bxc5 b4 14 Nd5 Nxc5
const sideMoves = ["dxe5", "dxe5", "bxc5", "b4", "Nd5", "Nxc5"];
let idx = 0;
for (const m of sideMoves) {
  try {
    chess.move(m);
    console.log(`Side Step ${idx} (${m}) success`);
    idx++;
  } catch (e: any) {
    console.error(`Failed at Side Step ${idx} (${m}): ${e.message}`);
    break;
  }
}
console.log(chess.ascii());
