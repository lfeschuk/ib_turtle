import { Chess } from 'chess.js';

function cleanMoveStr(m: string): string {
  return m.replace(/[!?+#=]+/g, '');
}

const chess = new Chess();
const initial = "1 d4 Nf6 2 c4 g6 3 Nc3 Bg7 4 e4 d6 5 f4 O-O 6 Nf3 c5 7 dxc5 Qa5";
const mainInteractive = "8 Bd3 Qxc5 9 Qe2 Nc6 10 Be3 Qa5 11 O-O Bg4 12 Rac1";

const moves = (initial + " " + mainInteractive).split(/\s+/).filter(Boolean);

for (let i = 0; i < moves.length; i++) {
  const move = moves[i];
  if (/^\d+\.?$/.test(move)) continue;
  const cleanMove = move.replace(/^\d+\.\.\./, '');
  const cleaned = cleanMoveStr(cleanMove);
  console.log(`Playing move ${move} (cleaned: ${cleaned})...`);
  if (!chess.move(cleaned)) {
    console.error(`FAILED at move: ${move}`);
    console.log("Current board:\n" + chess.ascii());
    break;
  }
  console.log("FEN:", chess.fen());
}
