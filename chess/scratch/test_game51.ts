import { Chess } from 'chess.js';

function cleanMoveStr(m: string): string {
  return m.replace(/[!?+#=]+/g, '');
}

function playMoves(chess: Chess, movesStr: string) {
  const moves = movesStr.trim().split(/\s+/).filter(Boolean);
  for (let i = 0; i < moves.length; i++) {
    const move = moves[i];
    if (/^\d+\.?$/.test(move)) continue;
    const cleanMove = move.replace(/^\d+\.\.\./, '');
    const cleaned = cleanMoveStr(cleanMove);
    if (!chess.move(cleaned)) {
      throw new Error("Failed to play move: " + move + " (cleaned: " + cleaned + ") at index " + i);
    }
  }
}

try {
  console.log("Testing Game 51 Main Line...");
  const chess = new Chess();
  
  // Initial moves
  const initial = "1 d4 Nf6 2 c4 g6 3 Nc3 Bg7 4 e4 d6 5 f4 O-O 6 Nf3 c5 7 dxc5 Qa5";
  playMoves(chess, initial);
  console.log("Initial moves played successfully. FEN:", chess.fen());
  const fenAfterInitial = chess.fen();

  // Main line interactive section
  const mainInteractive = "8 Bd3 Qxc5 9 Qe2 Nc6 10 Be3 Qa5 11 O-O Bg4 12 Rac1 Nd7 13 Qf2 Nc5 14 Bb1 Bxf3 15 gxf3 Na4 16 Nxa4 Qxa4 17 Rfd1 b6 18 Kh1 Rac8 19 h4 Rc7 20 h5 Nb4 21 hxg6 fxg6 22 b3 Qa5 23 Rg1 Kh8 24 Rg5 Qa3 25 Qh2 e5 26 Rcg1 Nc6 27 Rxg6 exf4 28 Bc1 Qc5 29 e5 Nxe5 30 Re6 Bf6 31 Qh6";
  playMoves(chess, mainInteractive);
  console.log("Main line played successfully. FEN:", chess.fen());
  const fenMain = chess.fen();

  // Test Sideline 1 (12 a3)
  console.log("\nTesting Sideline 1 (12 a3)...");
  const chessS1 = new Chess(fenAfterInitial);
  playMoves(chessS1, "8 Bd3 Qxc5 9 Qe2 Nc6 10 Be3 Qa5 11 O-O Bg4");
  playMoves(chessS1, "12 a3 Nd7 13 b4 Qh5 14 Qd2 Bxf3 15 Rxf3 Nd4 16 Rh3 Qxh3 17 gxh3 Nf3+");
  console.log("Sideline 1 successful. FEN:", chessS1.fen());

  // Test Sideline 2 (17...Rac8)
  console.log("\nTesting Sideline 2 (17...Rac8)...");
  const chessS2 = new Chess(fenAfterInitial);
  playMoves(chessS2, "8 Bd3 Qxc5 9 Qe2 Nc6 10 Be3 Qa5 11 O-O Bg4 12 Rac1 Nd7 13 Qf2 Nc5 14 Bb1 Bxf3 15 gxf3 Na4 16 Nxa4 Qxa4 17 Rfd1");
  playMoves(chessS2, "17...Rac8 18 b3 Qa5 19 Rd5 Qc7 20 Rcd1 b6 21 a3 Rfd8 22 h4 e6 23 Rg5 Qe7 24 h5 Qf6");
  console.log("Sideline 2 successful. FEN:", chessS2.fen());

  // Test Sideline 3 (23...Qh5+)
  console.log("\nTesting Sideline 3 (23...Qh5+)...");
  const chessS3 = new Chess(fenAfterInitial);
  playMoves(chessS3, "8 Bd3 Qxc5 9 Qe2 Nc6 10 Be3 Qa5 11 O-O Bg4 12 Rac1 Nd7 13 Qf2 Nc5 14 Bb1 Bxf3 15 gxf3 Na4 16 Nxa4 Qxa4 17 Rfd1 b6 18 Kh1 Rac8 19 h4 Rc7 20 h5 Nb4 21 hxg6 fxg6 22 b3 Qa5 23 Rg1");
  playMoves(chessS3, "23...Qh5+ 24 Kg2");
  console.log("Sideline 3 successful. FEN:", chessS3.fen());

} catch (err: any) {
  console.error("ERROR:", err.message || err);
  process.exit(1);
}
