import { Chess } from 'chess.js';

const chess = new Chess();
const prepMoves = [
  'd4', 'Nf6', 'c4', 'g6', 'Nc3', 'Bg7', 'e4', 'd6', 'Nf3', 'O-O',
  'Be2', 'e5', 'O-O', 'Nc6', 'd5', 'Ne7', 'b4', 'Nh5', 'g3', 'f5',
  'Ng5', 'Nf6', 'f3', 'f4', 'Kg2', 'c6', 'Qb3', 'h6', 'Ne6', 'Bxe6',
  'dxe6', 'Qc8', 'Rd1', 'Qxe6'
];

for (const m of prepMoves) {
  try {
    chess.move(m);
  } catch (e: any) {
    console.error(`Failed on prep move ${m}: ${e.message}`);
    process.exit(1);
  }
}

console.log("Position before 18 Rxd6:");
console.log(chess.ascii());

try {
  chess.move('Rxd6');
  console.log("After 18 Rxd6:");
  console.log(chess.ascii());
} catch (e: any) {
  console.error(`Failed to play 18 Rxd6: ${e.message}`);
  process.exit(1);
}

try {
  chess.move('Qxd6');
  console.log("After 18...Qxd6:");
  console.log(chess.ascii());
} catch (e: any) {
  console.error(`Failed to play 18...Qxd6: ${e.message}`);
  process.exit(1);
}

try {
  chess.move('c5+');
  console.log("After 19 c5+:");
  console.log(chess.ascii());
  console.log("Is check?", chess.inCheck());
} catch (e: any) {
  console.error(`Failed to play 19 c5+: ${e.message}`);
  process.exit(1);
}

console.log("Exercise 4 verified successfully!");
