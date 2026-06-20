import { Chess } from 'chess.js';

const chess = new Chess();
const prepMoves = [
  'd4', 'Nf6', 'c4', 'g6', 'Nc3', 'Bg7', 'e4', 'd6', 'f3', 'O-O',
  'Bg5', 'c5', 'd5', 'e6', 'Qd2', 'exd5', 'Nxd5', 'Be6', 'Ne2', 'Nc6',
  'Nec3', 'Bxd5', 'Nxd5', 'h6'
];

for (const m of prepMoves) {
  try {
    chess.move(m);
  } catch (e: any) {
    console.error(`Failed on prep move ${m}: ${e.message}`);
    process.exit(1);
  }
}

console.log("Position before 13 Bxh6:");
console.log(chess.ascii());

try {
  chess.move('Bxh6');
  console.log("After 13 Bxh6:");
  console.log(chess.ascii());
} catch (e: any) {
  console.error(`Failed to play 13 Bxh6: ${e.message}`);
  process.exit(1);
}

try {
  chess.move('Nxe4');
  console.log("After 13...Nxe4:");
  console.log(chess.ascii());
} catch (e: any) {
  console.error(`Failed to play 13...Nxe4: ${e.message}`);
  process.exit(1);
}

try {
  chess.move('fxe4');
  console.log("After 14 fxe4:");
  console.log(chess.ascii());
} catch (e: any) {
  console.error(`Failed to play 14 fxe4: ${e.message}`);
  process.exit(1);
}

try {
  chess.move('Qh4+');
  console.log("After 14...Qh4+:");
  console.log(chess.ascii());
  console.log("Is check?", chess.inCheck());
} catch (e: any) {
  console.error(`Failed to play 14...Qh4+: ${e.message}`);
  process.exit(1);
}

console.log("Exercise 6 verified successfully!");
