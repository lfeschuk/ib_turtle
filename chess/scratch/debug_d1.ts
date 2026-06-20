import { Chess } from 'chess.js';

const chess = new Chess();
const moves = [
  "d4", "Nf6", "c4", "g6", "Nc3", "Bg7", "e4", "d6", "f4", "O-O", "Nf3", "Na6", "Be2", "e5", "dxe5", "dxe5",
  "Qxd8", "Rxd8", "Nxe5", "Nc5", "Bf3", "Be6",
  "Nd5", "Nfd7", "Nxd7", "Rxd7", "O-O", "c6", "Ne3", "Rd4", "b3", "Nxe4", "Bb2", "Nd2", "Bxd2", "Rxd2"
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
