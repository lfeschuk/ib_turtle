import { Chess } from 'chess.js';

const chess = new Chess();
const prepMoves = [
  'd4', 'Nf6', 'c4', 'g6', 'Nc3', 'Bg7', 'e4', 'd6', 'f3', 'O-O',
  'Bg5', 'c5', 'd5', 'e6', 'Qd2', 'exd5', 'cxd5', 'a6', 'a4', 'Re8',
  'Nge2', 'Nbd7', 'Nc1', 'h6', 'Bxh6'
];

for (const m of prepMoves) {
  try {
    chess.move(m);
  } catch (e: any) {
    console.error(`Failed on move ${m}: ${e.message}`);
    process.exit(1);
  }
}

console.log("Position after 13 Bxh6:");
console.log(chess.ascii());

console.log("Testing 13...Nxe4");
try {
  chess.move('Nxe4');
  console.log(chess.ascii());
} catch (e: any) {
  console.error(`Failed 13...Nxe4: ${e.message}`);
  process.exit(1);
}

console.log("Testing 14 fxe4");
try {
  chess.move('fxe4');
  console.log(chess.ascii());
} catch (e: any) {
  console.error(`Failed 14 fxe4: ${e.message}`);
  process.exit(1);
}

console.log("Testing 14...Qh4+");
try {
  chess.move('Qh4+');
  console.log(chess.ascii());
} catch (e: any) {
  console.error(`Failed 14...Qh4+: ${e.message}`);
  process.exit(1);
}

console.log("Verification of candidate successful!");
