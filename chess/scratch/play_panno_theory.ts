import { Chess } from 'chess.js';

const chess = new Chess();

const moves = [
  "d4", "Nf6", "c4", "g6", "Nf3", "Bg7", "g3", "O-O", "Bg2", "d6", 
  "O-O", "Nc6", "Nc3", "a6", "d5", "Na5", "Nd2", "c5", 
  "Qc2", "Rb8", "b3", "b5", "Bb2", "Bh6", "f4", "bxc4", "bxc4", "e5"
];

let idx = 0;
for (const m of moves) {
  try {
    chess.move(m);
    console.log(`Step ${idx} (${m}) success`);
    idx++;
  } catch (e: any) {
    console.error(`Failed at step ${idx} (${m}): ${e.message}`);
    break;
  }
}

console.log(chess.ascii());
console.log("Legal moves for White now:");
console.log(chess.moves().join(", "));
