import { Chess } from 'chess.js';

function cleanMoveStr(m: string): string {
  return m.replace(/[!?+#=]+/g, '');
}

function playMoves(chess: Chess, movesStr: string) {
  const moves = movesStr.trim().split(/\s+/).filter(Boolean);
  for (let i = 0; i < moves.length; i++) {
    const move = moves[i];
    if (/^\d+\.?$/.test(move)) continue;
    // Handle move like 9...Bf5 or 24...Bxf4!! by stripping the prefix
    const cleanMove = move.replace(/^\d+\.\.\./, '');
    const cleaned = cleanMoveStr(cleanMove);
    if (!chess.move(cleaned)) {
      throw new Error(`Failed to play move: ${move} (cleaned: ${cleaned}) at index ${i}`);
    }
  }
}

try {
  console.log("Testing Game 50 Main Line...");
  const chess = new Chess();
  
  // Initial moves
  const initial = "1 d4 Nf6 2 c4 d6 3 Nc3 g6 4 e4 Bg7 5 f4 O-O 6 Nf3 c5 7 d5 e6 8 Be2 exd5 9 exd5";
  playMoves(chess, initial);
  console.log("Initial moves played successfully. FEN:", chess.fen());
  const fenAfterInitial = chess.fen();

  // Main line interactive section
  const mainInteractive = "9...Bf5 10 O-O Re8 11 Bd3 Qd7 12 h3 Na6 13 a3 Nc7 14 g4 Bxg4 15 hxg4 Qxg4+ 16 Kh2 Qh5+ 17 Kg2 Qg4+ 18 Kh2 b5 19 Rg1 Qh5+ 20 Kg3 bxc4 21 Bxc4 Re7 22 Qd3 Bh6 23 Kg2 Rae8 24 Bd2 Bxf4 25 Bxf4 Qg4+ 26 Bg3 Re3 27 Qf1 Nh5 28 Kh2 Rxf3 29 Qh3 Qxc4";
  playMoves(chess, mainInteractive);
  console.log("Main line played successfully. FEN:", chess.fen());
  const fenMain = chess.fen();

  // Test Sideline 1 (9...Nh5)
  console.log("\nTesting Sideline 1 (9...Nh5)...");
  const chessS1 = new Chess(fenAfterInitial);
  playMoves(chessS1, "9...Nh5 10 O-O Bxc3 11 bxc3 f5");
  console.log("Sideline 1 (f5) successful. FEN:", chessS1.fen());

  const chessS1b = new Chess(fenAfterInitial);
  playMoves(chessS1b, "9...Nh5 10 O-O Bxc3 11 bxc3 Ng7 12 f5");
  console.log("Sideline 1 (Ng7) successful. FEN:", chessS1b.fen());

  // Test Sideline 2 (11 Nh4)
  console.log("\nTesting Sideline 2 (11 Nh4)...");
  const chessS2 = new Chess(fenAfterInitial);
  // Play main moves up to 10...Re8 (index 2: 9...Bf5, 10 O-O, 10...Re8)
  playMoves(chessS2, "9...Bf5 10 O-O Re8");
  playMoves(chessS2, "11 Nh4 Ne4 12 Nxf5 gxf5 13 Nxe4 fxe4");
  console.log("Sideline 2 successful. FEN:", chessS2.fen());

  // Test Sideline 3 (11...Ne4)
  console.log("\nTesting Sideline 3 (11...Ne4)...");
  const chessS3 = new Chess(fenAfterInitial);
  playMoves(chessS3, "9...Bf5 10 O-O Re8 11 Bd3");
  playMoves(chessS3, "11...Ne4 12 Nxe4 Bxe4 13 Bxe4 Rxe4 14 Ng5");
  console.log("Sideline 3 successful. FEN:", chessS3.fen());

  // Test Sideline 4 (12 Nh4)
  console.log("\nTesting Sideline 4 (12 Nh4)...");
  const chessS4 = new Chess(fenAfterInitial);
  playMoves(chessS4, "9...Bf5 10 O-O Re8 11 Bd3 Qd7");
  playMoves(chessS4, "12 Nh4 Ne4");
  console.log("Sideline 4 successful. FEN:", chessS4.fen());

  // Test Sideline 5 (14 Qc2)
  console.log("\nTesting Sideline 5 (14 Qc2)...");
  const chessS5 = new Chess(fenAfterInitial);
  playMoves(chessS5, "9...Bf5 10 O-O Re8 11 Bd3 Qd7 12 h3 Na6 13 a3 Nc7");
  playMoves(chessS5, "14 Qc2 b5");
  console.log("Sideline 5 successful. FEN:", chessS5.fen());

  // Test Sideline 6 (14...Bxd3)
  console.log("\nTesting Sideline 6 (14...Bxd3)...");
  const chessS6 = new Chess(fenAfterInitial);
  playMoves(chessS6, "9...Bf5 10 O-O Re8 11 Bd3 Qd7 12 h3 Na6 13 a3 Nc7 14 g4");
  playMoves(chessS6, "14...Bxd3 15 Qxd3 b5 16 cxb5 Reb8 17 a4 a6");
  console.log("Sideline 6 successful. FEN:", chessS6.fen());

  // Test Sideline 7 (18 Kh1)
  console.log("\nTesting Sideline 7 (18 Kh1)...");
  const chessS7 = new Chess(fenAfterInitial);
  playMoves(chessS7, "9...Bf5 10 O-O Re8 11 Bd3 Qd7 12 h3 Na6 13 a3 Nc7 14 g4 Bxg4 15 hxg4 Qxg4+ 16 Kh2 Qh5+ 17 Kg2 Qg4+");
  playMoves(chessS7, "18 Kh1 Qh3+ 19 Nh2 Nh5");
  console.log("Sideline 7 successful. FEN:", chessS7.fen());

  // Test Sideline 8 (20 Kg2)
  console.log("\nTesting Sideline 8 (20 Kg2)...");
  const chessS8 = new Chess(fenAfterInitial);
  playMoves(chessS8, "9...Bf5 10 O-O Re8 11 Bd3 Qd7 12 h3 Na6 13 a3 Nc7 14 g4 Bxg4 15 hxg4 Qxg4+ 16 Kh2 Qh5+ 17 Kg2 Qg4+ 18 Kh2 b5 19 Rg1 Qh5+");
  playMoves(chessS8, "20 Kg2");
  console.log("Sideline 8 successful. FEN:", chessS8.fen());

} catch (err: any) {
  console.error("ERROR:", err.message || err);
  process.exit(1);
}
