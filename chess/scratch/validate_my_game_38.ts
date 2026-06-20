import { Chess } from 'chess.js';

const initialMoves = "1. d4 Nf6 2. c4 g6 3. Nc3 Bg7 4. e4 d6 5. f3 O-O 6. Bg5 c5 7. d5 e6 8. Qd2 exd5 9. cxd5 a6 10. a4 h6 11. Be3";

const mainMoves = [
  "Rdf8", "Nge2", "Nbd7", "Nf4", "Ne5", "Be2", "Bd7", "O-O", "Ne8", "Rfb1", "a5",
  "Nb5", "Bxb5", "Bxb5", "Nc7", "Bf1", "Qd7", "Rd1", "Kh7", "h3", "b6", "b3", "f5",
  "exf5", "Qxf5", "Rac1", "Rae8", "Bb5", "Re7", "Ne6", "Nxe6", "dxe6", "Qxe6",
  "Bg5", "Nxf3+", "gxf3", "Bd4+", "Kh1", "Rxf3", "Bf1", "Qe4", "Kh2", "Ref7",
  "Bg2", "Be5+", "Kg1", "R7f2", "Bxf3", "Bd4+"
];

const options = [
  { name: "Be3", move: "Be3" },
  { name: "Rd2", move: "Rd2" },
  { name: "Qe3", move: "Qe3" },
  { name: "Qe2", move: "Qe2" },
  { name: "Kf1", move: "Kf1" },
  { name: "Kh1", move: "Kh1" },
];

function cleanMoveStr(m: string): string {
  return m.replace(/[!?+#=]+/g, '');
}

function runTest(option: { name: string, move: string }) {
  const chess = new Chess();
  
  // Play initial
  const initial = initialMoves.trim().split(/\s+/).filter(Boolean);
  for (let move of initial) {
    if (/^\d+\.?$/.test(move)) continue;
    const clean = cleanMoveStr(move);
    chess.move(clean);
  }
  
  // Play main
  let count = 0;
  for (let move of mainMoves) {
    const clean = cleanMoveStr(move);
    try {
      chess.move(clean);
      count++;
    } catch (err: any) {
      console.log(`Failed at main move ${count}: ${move}`);
      console.log(chess.ascii());
      throw err;
    }
  }
  
  // Try option
  try {
    const cleanOption = cleanMoveStr(option.move);
    const result = chess.move(cleanOption);
    if (result) {
      console.log(`Option ${option.name} is VALID!`);
      // Try next move in game: 36...Rxf3
      try {
        const nextResult = chess.move("Rxf3");
        if (nextResult) {
          console.log(`  Follow-up 36...Rxf3 is also VALID!`);
          console.log(`  FEN: ${chess.fen()}`);
        } else {
          console.log(`  Follow-up 36...Rxf3 is INVALID (returned null)`);
        }
      } catch (err: any) {
        console.log(`  Follow-up 36...Rxf3 failed:`, err.message || err);
      }
    } else {
      console.log(`Option ${option.name} is INVALID (returned null)`);
    }
  } catch (err: any) {
    console.log(`Option ${option.name} failed:`, err.message || err);
  }
}

console.log("Starting validation tests...");
for (const opt of options) {
  runTest(opt);
}
