import { Chess } from 'chess.js';

const chess = new Chess();
// Play moves to reach the promotion position
const moves = "1 d4 Nf6 2 c4 g6 3 Nc3 Bg7 4 e4 d6 5 f3 O-O 6 Be3 Nc6 7 Qd2 a6 8 Nge2 Rb8 9 Nc1 e5 10 d5 Nd4 11 Nb3 c5 12 dxc6 Nxb3 13 c7 Nxd2".split(/\s+/).filter(Boolean);
for (const m of moves) {
  if (!/^\d+\.?$/.test(m)) chess.move(m);
}
console.log("FEN before promotion:", chess.fen());
try {
  // Test with =
  const c1 = new Chess(chess.fen());
  console.log("Move with '=':", c1.move("cxb8=Q"));
} catch (e) {
  console.log("Move with '=' failed:", e);
}

try {
  // Test without = (cleaned)
  const c2 = new Chess(chess.fen());
  console.log("Move without '=':", c2.move("cxb8Q"));
} catch (e) {
  console.log("Move without '=' failed:", e);
}
