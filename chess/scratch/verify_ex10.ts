import { Chess } from 'chess.js';

const chess = new Chess();
const prepMoves = [
  'd4', 'Nf6', 'c4', 'g6', 'Nc3', 'Bg7', 'e4', 'd6', 'Nf3', 'O-O',
  'h3', 'e5', 'd5', 'Na6', 'Bg5', 'Qe8', 'g4', 'Nd7', 'Rg1', 'Kh8',
  'a3', 'f5', 'gxf5', 'gxf5', 'b4', 'Nf6', 'Bd3', 'Nxe4', 'Nxe4', 'fxe4',
  'Bxe4', 'Bf5', 'Nd2', 'Qg6', 'Rg4', 'Bh6', 'Bxh6', 'Qxh6', 'Bxf5', 'Rxf5',
  'Rg3', 'Raf8', 'Ne4', 'Rf4', 'Qe2', 'Qh4', 'Re3'
];

for (const m of prepMoves) {
  try {
    chess.move(m);
  } catch (e: any) {
    console.error(`Failed on move ${m}: ${e.message}`);
    process.exit(1);
  }
}

console.log("Position after 24 Re3:");
console.log(chess.ascii());

const solutionMoves = [
  'Nb8' // 24...Nb8!
];

let moveNum = 24;
let player = 'B';

for (const step of solutionMoves) {
  console.log(`Playing ${moveNum}${player === 'W' ? '.' : '...'} ${step}`);
  try {
    const result = chess.move(step);
    if (result) {
      console.log(chess.ascii());
    } else {
      console.error(`Failed to play ${step}: returned null`);
      process.exit(1);
    }
  } catch (e: any) {
    console.error(`Failed to play ${step}: ${e.message}`);
    process.exit(1);
  }
  
  if (player === 'B') {
    player = 'W';
    moveNum++;
  } else {
    player = 'B';
  }
}

console.log("Verification of Exercise 10 successful!");
