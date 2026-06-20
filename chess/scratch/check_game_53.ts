import { Chess } from 'chess.js';

const chess = new Chess();

const moves = [
  "d4", "Nf6", "c4", "g6", "Nc3", "Bg7", "e4", "d6", "f4", "O-O",
  "Nf3", "Na6", "Bd3", "Bg4", "O-O", "Nd7", "Be3", "e5", "fxe5", "c5",
  "d5", "Nxe5", "Be2", "Nxf3+", "Bxf3", "Bxf3", "Qxf3", "Qe7",
  "Bf4", "Nc7", "Qg3", "Rad8", "Kh1", "Bd4", "Rae1", "f6", "Ne2", "Be5",
  "Ng1", "Bxf4", "Qxf4", "Na6", "Qd2", "Rde8", "Nf3", "Nb8", "Qc3", "Nd7",
  "b3", "Ne5", "Nd2"
];

for (let i = 0; i < moves.length; i++) {
  const move = moves[i];
  try {
    const result = chess.move(move);
    if (!result) {
      throw new Error(`chess.js returned null`);
    }
    console.log(`${i+1}. ${move} ok. FEN: ${chess.fen()}`);
  } catch (err: any) {
    console.error(`Error at move ${i+1} (${move}): ${err.message}`);
    console.log(chess.ascii());
    break;
  }
}
