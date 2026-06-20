import { Chess } from 'chess.js';

const chess = new Chess();
const moves = [
  "d4", "Nf6", "c4", "g6", "Nc3", "Bg7", "e4", "d6", "f4", "O-O", "Nf3", "Na6", "Be2", "e5", "dxe5", "dxe5",
  "Qxd8", "Rxd8", "Nxe5", "Nc5", "Bf3", "Be6",
  "O-O", "Nfd7", "Nxd7", "Bd4+", "Kh1", "Rxd7", "Nd5", "c6", "Be3", "cxd5", "Bxd4", "dxe4", "Bxc5", "exf3", "Rxf3", "Bxc4"
];

for (let i = 0; i < moves.length; i++) {
  const m = moves[i];
  console.log(`\nMove ${i+1}: ${m}`);
  try {
    const result = chess.move(m);
    if (!result) {
      console.log("Failed to play move, returned null");
      break;
    }
    console.log(chess.ascii());
  } catch (e: any) {
    console.log("Error:", e.message);
    break;
  }
}
