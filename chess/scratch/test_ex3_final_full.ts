import { Chess } from 'chess.js';

const chess = new Chess();
const prepMoves = [
  'd4', 'Nf6', 'c4', 'g6', 'Nc3', 'Bg7', 'e4', 'd6', 'Nf3', 'O-O',
  'Be2', 'e5', 'O-O', 'Nc6', 'd5', 'Ne7', 'Ne1', 'Nd7', 'Be3', 'f5',
  'f3', 'f4', 'Bf2', 'g5', 'Rc1', 'Rf6', 'Nd3', 'Rh6', 'b4', 'Qe8',
  'Kh1', 'Qh5', 'Bg1', 'Nf6', 'Nb5'
];

console.log("Applying prep moves...");
for (const move of prepMoves) {
  chess.move(move);
}

const solutionMoves = [
  'Qh4', // 18...Qh4!!
  'g3',  // 19 g3
  'fxg3',// 19...fxg3
  'Nxc7',// 20 Nxc7
  'Ng6', // 20...Ng6!
  'Nxa8',// 21 Nxa8?
  'Qxh2+',// 21...Qxh2+!
  'Bxh2',// 22 Bxh2
  'Rxh2+',// 22...Rxh2+
  'Kg1', // 23 Kg1
  'Nf4', // 23...Nf4
  'Rf2', // 24 Rf2
  'Nh3+',// 24...Nh3+
  'Kf1', // 25 Kf1
  'Rxf2#'// 25...Rxf2#
];

let moveNum = 18;
let player = 'B';

for (const step of solutionMoves) {
  console.log(`Playing ${moveNum}${player === 'B' ? '...' : '.'} ${step}`);
  chess.move(step);
  console.log(chess.ascii());
  if (player === 'B') {
    player = 'W';
    moveNum++;
  } else {
    player = 'B';
  }
}
console.log("Success!");
