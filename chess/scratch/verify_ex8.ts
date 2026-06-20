import { Chess } from 'chess.js';

const chess = new Chess();
const prepMoves = [
  'd4', 'Nf6', 'c4', 'g6', 'Nc3', 'Bg7', 'e4', 'd6', 'f4', 'O-O',
  'Nf3', 'Na6', 'Be2', 'e5', 'dxe5', 'dxe5', 'Nxe5', 'Nc5', 'Qc2'
];

for (const m of prepMoves) {
  try {
    chess.move(m);
  } catch (e: any) {
    console.error(`Failed on move ${m}: ${e.message}`);
    process.exit(1);
  }
}

console.log("Position after 10 Qc2:");
console.log(chess.ascii());

// Main line of solution
const mainLine = ['Nfxe4', 'Nxe4', 'Bf5'];
const chessMain = new Chess(chess.fen());
console.log("Testing Main Line:");
for (const m of mainLine) {
  try {
    chessMain.move(m);
    console.log(chessMain.ascii());
  } catch (e: any) {
    console.error(`Failed on main line move ${m}: ${e.message}`);
    process.exit(1);
  }
}

// Sideline A
const sideA = ['Bf3', 'Qd4'];
const chessA = new Chess(chessMain.fen());
console.log("Testing Sideline A (after 11...Bf5):");
for (const m of sideA) {
  try {
    chessA.move(m);
    console.log(chessA.ascii());
  } catch (e: any) {
    console.error(`Failed on side A move ${m}: ${e.message}`);
    process.exit(1);
  }
}

// Sideline B
const sideB = ['Nd2', 'Qd4', 'Bf3', 'Rad8'];
const chessB = new Chess(chessMain.fen());
console.log("Testing Sideline B (after 11...Bf5):");
for (const m of sideB) {
  try {
    chessB.move(m);
    console.log(chessB.ascii());
  } catch (e: any) {
    console.error(`Failed on side B move ${m}: ${e.message}`);
    process.exit(1);
  }
}

console.log("Verification of Exercise 8 successful!");
