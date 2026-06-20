import { Chess } from 'chess.js';

const chess = new Chess();
const prepMoves = [
  'd4', 'Nf6', 'Nf3', 'g6', 'c4', 'Bg7', 'Nc3', 'O-O', 'e4', 'd6',
  'Be2', 'e5', 'O-O', 'Nc6', 'd5', 'Ne7', 'Ne1', 'Nd7', 'Be3', 'f5',
  'f3', 'f4', 'Bf2', 'g5', 'Rc1', 'Rf6', 'b4', 'Rh6', 'c5', 'Qe8',
  'Kh1', 'Nf6', 'Nb5', 'Qh5', 'Bg1'
];

for (const m of prepMoves) {
  try {
    chess.move(m);
  } catch (e: any) {
    console.error(`Failed on move ${m}: ${e.message}`);
    process.exit(1);
  }
}

console.log("Position after 18 Bg1:");
console.log(chess.ascii());

const solutionMoves = [
  { move: 'Qh4', annot: '!!' },
  { move: 'g3' },
  { move: 'fxg3' },
  { move: 'Nxc7' },
  { move: 'Ng6', annot: '!' },
  { move: 'Nxa8' },
  { move: 'Qxh2+', annot: '!' },
  { move: 'Bxh2' },
  { move: 'Rxh2+', annot: '' },
  { move: 'Kg1' },
  { move: 'Nf4' },
  { move: 'Rf2' },
  { move: 'Nh3+', annot: '' },
  { move: 'Kf1' },
  { move: 'Rxf2#', annot: '' }
];

let moveNum = 18;
let player = 'B';

for (const step of solutionMoves) {
  const moveStr = step.move;
  console.log(`Playing ${moveNum}${player === 'B' ? '...' : '.'} ${moveStr}`);
  try {
    const result = chess.move(moveStr);
    if (result) {
      console.log(chess.ascii());
    } else {
      console.error(`Failed to play ${moveStr}: returned null`);
      process.exit(1);
    }
  } catch (e: any) {
    console.error(`Failed to play ${moveStr}: ${e.message}`);
    process.exit(1);
  }
  
  if (player === 'B') {
    player = 'W';
    moveNum++;
  } else {
    player = 'B';
  }
}

console.log("Verification successful!");
