import { Chess } from "chess.js";

const chess = new Chess();

const initial = "d4 Nf6 c4 g6 Nc3 Bg7 e4 d6 Nf3 O-O Be2 e5 O-O Nc6 d5 Ne7 Ne1 Nd7 Be3 f5 f3 f4 Bf2 g5";
for (const m of initial.split(" ")) {
  if (m === "12") continue;
  chess.move(m);
}

const moves = [
  "a4", "a5", "Nd3", "b6", "b4", "axb4", "Nb5", "Nf6", "Be1", "g4",
  "Bxb4", "g3", "h3", "Bxh3", "gxh3", "Qd7", "Qc2", "Qxh3", "Bd1", "Ng6",
  "Qg2", "Qh6", "Qh1", "Nh4", "Ne1", "Nxe4", "Ng2", "Rf5", "fxe4", "f3",
  "Bxf3", "Nxf3+", "Rxf3", "Qxh1+", "Kxh1", "Rxf3", "Kg1", "Rb3", "Nxc7", "Rf8",
  "Be1", "Bf6", "Nb5", "Be7", "Ra3", "Rxa3", "Nxa3", "Rf3", "Nc2", "Bg5",
  "Bb4", "h5", "Nce1", "Rf6", "a5", "bxa5", "Bxa5", "Rf2", "Bc7", "Be7",
  "Nd3", "Re2", "Nf2", "Ra2", "c5", "Ra1+", "Nfe1", "h4", "Nxh4", "Bxh4",
  "Bxd6", "Re1", "c6", "Rxe4", "c7", "Rc4", "Bxe5", "Kf7", "Nxg3", "Bxg3"
];

for (let i = 0; i < moves.length; i++) {
  const m = moves[i];
  try {
    chess.move(m);
  } catch (e: any) {
    console.error(`Failed at move ${i} (${m}):`, e.message);
    break;
  }
}

console.log("Game valid?", !chess.inCheck() && chess.history().length === moves.length + 80); // 80 is approx length of initial?
// Let's just check if it reached the end.
console.log("Final FEN:", chess.fen());
console.log("History length:", chess.history().length);
// Initial moves count:
const initialCount = initial.split(" ").filter(m => m !== "12").length;
console.log("Expected total moves:", initialCount + moves.length);
