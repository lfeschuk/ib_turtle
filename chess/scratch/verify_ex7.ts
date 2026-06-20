import { Chess } from 'chess.js';

const chess = new Chess();
const prepMoves = [
  'Nf3', 'Nf6', 'c4', 'g6', 'd4', 'Bg7', 'Nc3', 'O-O', 'g3', 'd6',
  'Bg2', 'Nbd7', 'O-O', 'e5', 'e4', 'c6', 'h3', 'Qa5', 'Re1', 'exd4',
  'Nxd4', 'Ne5', 'Bf1', 'Re8', 'Be3', 'Be6', 'Nxe6', 'Rxe6', 'Rb1'
];

for (const m of prepMoves) {
  try {
    chess.move(m);
  } catch (e: any) {
    console.error(`Failed on move ${m}: ${e.message}`);
    process.exit(1);
  }
}

console.log("Position after 15 Rb1:");
console.log(chess.ascii());

const solutionMoves = [
  'Nxe4', // 15...Nxe4!
  'Nxe4', // 16 Nxe4? (Wait, is it Nxe4? or something else?
  'Qxe1', // 16...Qxe1!
  'Qxe1', // 17 Qxe1
  'Nf3+'  // 17...Nf3+
];

let moveNum = 15;
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

console.log("Verification of Exercise 7 successful!");
