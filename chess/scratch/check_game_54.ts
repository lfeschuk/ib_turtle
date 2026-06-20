import { Chess } from 'chess.js';

function testMoves(moves: string[]) {
  const chess = new Chess();
  for (let i = 0; i < moves.length; i++) {
    const move = moves[i];
    try {
      const result = chess.move(move);
      if (!result) {
        throw new Error(`chess.js returned null`);
      }
    } catch (err: any) {
      console.error(`Error at move ${i+1} (${move}): ${err.message}`);
      console.log(chess.ascii());
      return false;
    }
  }
  console.log("All moves OK! FEN: " + chess.fen());
  return true;
}

const baseMoves = [
  "d4", "Nf6", "c4", "g6", "Nc3", "Bg7", "e4", "d6", "f4", "O-O",
  "Nf3", "Na6", "e5", "Nd7", "c5", "dxe5", "d5", "Nb6", "a3", "Nb8",
  "Be3", "c6", "dxc6", "Nxc6",
  "cxb6", "axb6",
  "fxe5", "Bg4", "Be2", "Rc8", "Qxd8", "Rfxd8",
  "Rd1", "Rxd1+", "Kxd1", "Bxf3", "Bxf3", "Nxe5",
  "Bxb6", "Nxf3", "Ba7", "Bxc3", "bxc3", "Rxc3", "gxf3", "Rxa3",
  "Re1", "Rxa7", "Rxe7", "Kg7"
];

const variation1 = [
  ...baseMoves,
  "f4", "Kf6", // 25. f4 Kf6
  "Rc7", "Ra4", // 26. Rc7 Ra4
  "f5", "Rf4",  // 27. f5 Rf4
  "fxg6", "hxg6", // 28. fxg6 hxg6
  "h4", "b5",   // 29. h4 b5
  "Ke2", "Ke6",  // 30. Ke2 Ke6
  "Rc6+", "Ke7", // 31. Rc6+ Ke7
  "h5", "gxh5", // 32. h5 gxh5
  "Rc5", "b4",   // 33. Rc5 b4
  "Rxh5", "Kd6", // 34. Rxh5 Kd6
  "Ke3", "Rc4",  // 35. Ke3 Rc4
  "Rf5", "b3",   // 36. Rf5 b3
  "Rb5", "Rc3+", // 37. Rb5 Rc3+
  "Ke4", "Kc6",  // 38. Ke4 Kc6
  "Rb8", "Kc5",  // 39. Rb8 Kc5
  "Kf4", "Rc4+",  // 40. Kf4 Rc4+ (corrected f4 to Kf4)
  "Ke5", "Rb4",  // 41. Ke5 Rb4
  "Rc8+", "Kb5"  // 42. Rc8+ Kb5
];

console.log("Testing Variation 1 to the end (with Kf4)...");
testMoves(variation1);
