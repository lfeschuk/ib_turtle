import { Chess } from 'chess.js';

const chess = new Chess();
const prepMoves = [
  'd4', 'Nf6', 'c4', 'g6', 'Nc3', 'Bg7', 'e4', 'd6', 'f4', 'O-O',
  'Nf3', 'Na6', 'Be2', 'e5', 'dxe5', 'dxe5', 'O-O', 'Nc5', 'Qc2'
];

for (const m of prepMoves) {
  chess.move(m);
}

console.log("Position after 10 Qc2 (with O-O):");
console.log(chess.ascii());

const mainLine = ['Nfxe4', 'Nxe4', 'Bf5'];
const chessMain = new Chess(chess.fen());
for (const m of mainLine) {
  chessMain.move(m);
}
console.log("Main Line OK.");

// Sideline 1: 12 Nfd2
console.log("Testing 12 Nfd2...");
const chessSide1 = new Chess(chessMain.fen());
const side1Moves = ['Nfd2', 'Nxe4', 'Nxe4', 'Qh4+'];
for (const m of side1Moves) {
  chessSide1.move(m);
}
console.log("Sideline 12 Nfd2 OK.");

// Sideline 2: 12 Bd3
console.log("Testing 12 Bd3...");
const chessSide2 = new Chess(chessMain.fen());
const side2Moves = ['Bd3', 'Bxe4', 'Bxe4', 'f5', 'Bd3', 'e4'];
for (const m of side2Moves) {
  chessSide2.move(m);
}
console.log("Sideline 12 Bd3 OK.");

console.log("All lines OK with O-O!");
