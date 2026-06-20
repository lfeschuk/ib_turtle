import { Chess } from 'chess.js';

const chess = new Chess();
const prepMoves = [
  'd4', 'Nf6', 'c4', 'g6', 'Nc3', 'Bg7', 'Nf3', 'd6',
  'Bg5', 'O-O', 'e3', 'Nbd7', 'Qc2', 'c6', 'Be2', 'e5',
  'Rd1', 'Qc7', 'O-O', 'h6', 'Bh4', 'g5', 'Bg3', 'Nh5'
];

for (const m of prepMoves) {
  try {
    chess.move(m);
  } catch (e: any) {
    console.error(`Failed on prep move ${m}: ${e.message}`);
    process.exit(1);
  }
}

console.log("Position before 13 Nxg5:");
console.log(chess.ascii());

// Test 13 Nxg5!
const chessMain = new Chess(chess.fen());
try {
  chessMain.move('Nxg5');
  console.log("After 13 Nxg5:");
  console.log(chessMain.ascii());
} catch (e: any) {
  console.error(`Failed to play 13 Nxg5: ${e.message}`);
  process.exit(1);
}

// Test Main Line: 13...hxg5 14 Bxh5
const chessMainLine = new Chess(chessMain.fen());
try {
  chessMainLine.move('hxg5');
  console.log("After 13...hxg5:");
  console.log(chessMainLine.ascii());
  chessMainLine.move('Bxh5');
  console.log("After 14 Bxh5:");
  console.log(chessMainLine.ascii());
  console.log("Main line verified!");
} catch (e: any) {
  console.error(`Failed on main line: ${e.message}`);
}

// Test Sideline: 13...Nxg3 14 Qh7#
const chessSide = new Chess(chessMain.fen());
try {
  chessSide.move('Nxg3');
  console.log("After 13...Nxg3:");
  console.log(chessSide.ascii());
  chessSide.move('Qh7#');
  console.log("After 14 Qh7#:");
  console.log(chessSide.ascii());
  console.log("Is game over?", chessSide.isGameOver());
  console.log("Is mate?", chessSide.isCheckmate());
  console.log("Sideline verified!");
} catch (e: any) {
  console.error(`Failed on sideline: ${e.message}`);
}
