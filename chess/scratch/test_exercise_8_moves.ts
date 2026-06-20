import { Chess } from 'chess.js';

const chess = new Chess();

const initialMoves = [
  "d4", "Nf6", "c4", "g6", "Nc3", "Bg7", "e4", "d6", "f4", "O-O",
  "Nf3", "Na6", "Be2", "e5", "dxe5", "dxe5", "Nxe5"
];

console.log("Playing initial moves...");
for (const m of initialMoves) {
  try {
    chess.move(m);
  } catch (e: any) {
    console.error(`Failed on initial move ${m}:`, e.message);
    process.exit(1);
  }
}

console.log("FEN after initial moves:", chess.fen());
console.log(chess.ascii());

const interactiveMoves = [
  { move: "Nc5", player: "B", num: 9 },
  { move: "Qc2", player: "W", num: 10 },
  { move: "Nfxe4", player: "B", num: 10 },
  { move: "Nxe4", player: "W", num: 11 },
  { move: "Bf5", player: "B", num: 11 },
  { move: "Bf3", player: "W", num: 12 },
  { move: "Bxe4", player: "B", num: 12 },
  { move: "Bxe4", player: "W", num: 13 },
  { move: "Qd4", player: "B", num: 13 }
];

console.log("Playing interactive moves...");
for (const step of interactiveMoves) {
  try {
    const result = chess.move(step.move);
    if (!result) {
      console.error(`Move returned null: ${step.num}${step.player} ${step.move}`);
      process.exit(1);
    }
    console.log(`Played ${step.num}${step.player} ${step.move}`);
    console.log(chess.ascii());
  } catch (e: any) {
    console.error(`Error playing ${step.num}${step.player} ${step.move}:`, e.message);
    process.exit(1);
  }
}

console.log("All moves are legal!");
