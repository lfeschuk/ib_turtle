import { Chess } from 'chess.js';

const chess = new Chess();
const moves = [
  'd4', 'Nf6', 'c4', 'g6', 'Nc3', 'Bg7', 'e4', 'd6', 'Nf3', 'O-O',
  'Be2', 'e5', 'O-O', 'Nc6', 'd5', 'Ne7', 'b4', 'Nh5', 'g3', 'f5',
  'Ng5', 'Nf6', 'f3', 'f4', 'Kg2', 'c6', 'Qb3', 'h6', 'Ne6', 'Bxe6',
  'dxe6', 'Qc8', 'Rd1', 'Qxe6'
];

let error = false;
for (let i = 0; i < moves.length; i++) {
  try {
    if (!chess.move(moves[i])) {
      console.error(`Move failed: ${moves[i]} at index ${i}`);
      error = true;
      break;
    }
  } catch (e: any) {
    console.error(`Error at move ${moves[i]}: ${e.message}`);
    error = true;
    break;
  }
}

if (!error) {
  console.log("Exercise 4 prep moves are VALID!");
  console.log("FEN:", chess.fen());
  console.log(chess.ascii());
}
