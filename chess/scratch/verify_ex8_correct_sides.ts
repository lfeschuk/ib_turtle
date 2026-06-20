import { Chess } from 'chess.js';

const chess = new Chess();
const prepMoves = [
  'd4', 'Nf6', 'c4', 'g6', 'Nc3', 'Bg7', 'e4', 'd6', 'f4', 'O-O',
  'Nf3', 'Na6', 'Be2', 'e5', 'dxe5', 'dxe5', 'O-O', 'Nc5', 'Qc2'
];

for (const m of prepMoves) {
  chess.move(m);
}

const mainLine = ['Nfxe4', 'Nxe4', 'Bf5'];

// Verify Main Line
const chessMain = new Chess(chess.fen());
console.log("Verifying Main Line...");
for (const m of mainLine) {
  chessMain.move(m);
}
console.log("Main Line OK.");

// Verify Sideline 1: 12 Nfd2
console.log("Verifying Sideline 12 Nfd2...");
const chessSide1 = new Chess(chessMain.fen());
const side1Moves = ['Nfd2', 'Nxe4', 'Nxe4', 'Qh4+'];
for (const m of side1Moves) {
  chessSide1.move(m);
}
console.log("Sideline 12 Nfd2 OK.");

// Verify Sideline 2: 12 Bd3
console.log("Verifying Sideline 12 Bd3...");
const chessSide2 = new Chess(chessMain.fen());
const side2Moves = ['Bd3', 'Bxe4', 'Bxe4', 'f5', 'Bd3', 'e4'];
for (const m of side2Moves) {
  chessSide2.move(m);
}
console.log("Sideline 12 Bd3 OK.");

console.log("All Exercise 8 lines verified successfully!");
