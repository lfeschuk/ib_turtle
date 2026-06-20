import { Chess } from 'chess.js';

const chess = new Chess();
const moves = [
  'd4', 'Nf6', 'c4', 'g6', 'Nc3', 'Bg7', 'e4', 'd6', 'Nf3', 'O-O',
  'Be2', 'e5', 'O-O', 'Nc6', 'd5', 'Ne7', 'Ne1', 'Nd7', 'Be3', 'f5',
  'f3', 'f4', 'Bf2', 'g5', 'Rc1', 'Rf6', 'Nd3', 'Rh6', 'b4', 'Qe8',
  'c5', 'Qh5', 'Nb5', 'Nf6', 'a3'
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
  console.log("All prep moves are VALID!");
  console.log("FEN:", chess.fen());
  console.log(chess.ascii());
}
