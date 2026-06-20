import { Chess } from 'chess.js';

const chess = new Chess();
const prepMoves = [
  'd4', 'Nf6', 'c4', 'g6', 'Nc3', 'Bg7', 'e4', 'd6', 'Nf3', 'O-O',
  'Be2', 'e5', 'O-O', 'Nbd7', 'Be3', 'Re8', 'd5', 'Nc5', 'Qc2', 'a6'
];

for (const m of prepMoves) {
  try {
    chess.move(m);
  } catch (e: any) {
    console.error(`Failed on move ${m}: ${e.message}`);
    process.exit(1);
  }
}

console.log("Position after 10...a6:");
console.log(chess.ascii());

const solutionMoves = [
  'b4',     // 11 b4?
  'Ncxe4',  // 11...Ncxe4!
  'Nxe4',   // 12 Nxe4
  'Nxe4',   // 12...Nxe4
  'Qxe4',   // 13 Qxe4
  'Bf5',    // 13...Bf5
  'Qd3',    // 14 Qd3
  'e4'      // 14...e4
];

let moveNum = 11;
let player = 'W';

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

console.log("Verification of Exercise 9 successful!");
