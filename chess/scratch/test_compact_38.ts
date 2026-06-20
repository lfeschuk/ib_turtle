import { Chess } from 'chess.js';

const initial = "d4 Nf6 c4 g6 Nc3 Bg7 e4 d6 f3 O-O Be3 c5 d5 e6 Qd2 exd5 cxd5 a6 a4 h6 Nge2 Nbd7 Ng3 Ne5 Be2";
const moves = [
  { m: "Re8" }, // Assumed 13...Re8
  { m: "Bxh6" },
  { m: "Nxe4" }, // f6 knight takes e4
  { m: "Ngxe4" }, // g3 knight takes e4
  { m: "Qh4+" },
  { m: "g3" },
  { m: "Qxh6" }
];

const chess = new Chess();
const initialMoves = initial.trim().split(/\s+/).filter(Boolean);

console.log("Playing initial moves:");
let isWhite = true;
for (let move of initialMoves) {
  const player = isWhite ? "W" : "B";
  chess.move(move);
  console.log(`${player}: ${move}`);
  isWhite = !isWhite;
}

console.log("\nPlaying main moves:");
for (let moveObj of moves) {
  const player = isWhite ? "W" : "B";
  try {
    const result = chess.move(moveObj.m);
    console.log(`${player}: ${moveObj.m} -> FEN: ${chess.fen()}`);
    isWhite = !isWhite;
  } catch (err: any) {
    console.log(`Failed at ${player}: ${moveObj.m}. Error: ${err.message}`);
    break;
  }
}
