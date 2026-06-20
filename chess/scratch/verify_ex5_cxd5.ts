import { Chess } from 'chess.js';

const chess = new Chess();
const prepMoves = [
  'd4', 'Nf6', 'c4', 'g6', 'Nc3', 'Bg7', 'e4', 'd6', 'f3', 'O-O',
  'Bg5', 'c5', 'd5', 'e6', 'Qd2', 'exd5', 'cxd5', 'a6', 'a4', 'h6',
  'Bxh6'
];

for (const m of prepMoves) {
  chess.move(m);
}

console.log("Position after 11 Bxh6:");
console.log(chess.ascii());

console.log("Testing 11...Nxe4");
chess.move('Nxe4');
console.log(chess.ascii());

console.log("Testing 12 Nxe4");
chess.move('Nxe4');
console.log(chess.ascii());


console.log("Testing 12...Qh4+");
chess.move('Qh4+');
console.log(chess.ascii());

console.log("Testing 13 g3");
chess.move('g3');
console.log(chess.ascii());

console.log("Testing 13...Qxh6");
chess.move('Qxh6');
console.log(chess.ascii());

console.log("Testing 14 Qxh6");
chess.move('Qxh6');
console.log(chess.ascii());

console.log("Testing 14...Bxh6");
chess.move('Bxh6');
console.log(chess.ascii());

console.log("Is 15 Nxd6 legal?");
try {
  const result = chess.move('Nxd6');
  if (result) {
    console.log("YES, Nxd6 is legal!");
    console.log(chess.ascii());
  } else {
    console.log("NO, Nxd6 is illegal.");
  }
} catch (e: any) {
  console.log(`NO, Nxd6 is illegal: ${e.message}`);
}
