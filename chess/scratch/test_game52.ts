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
      throw new Error(`Failed to play move: ${move} (cleaned: ${cleaned}) at index ${i}`);
    }
  }
}

try {
  console.log("Testing Game 52 Main Line...");
  const chess = new Chess();
  
  // Initial moves (up to 8 dxe5 dxe5)
  const initial = "1 d4 Nf6 2 c4 g6 3 Nc3 Bg7 4 e4 d6 5 f4 O-O 6 Nf3 Na6 7 Be2 e5 8 dxe5 dxe5";
  playMoves(chess, initial);
  console.log("Initial moves played. FEN:", chess.fen());
  const fenAfter8 = chess.fen();

  // Main line interactive
  // 9 Nxe5 Nc5 10 Bf3 Qxd1+ 11 Kxd1 Rd8+ 12 Kc2 Nfxe4 13 Nxe4 Bf5 14 Re1 Bxe5 15 fxe5 Rd4 16 Kc3 Rd3+ 17 Kc2 Rd4 18 Kc3 Rd3+ 19 Kb4 Na6+ 20 Ka5 b6+ 21 Page 136: Kxa6 Bc8+ 22 Kb5 Bd7+ 23 Ka6 Bc8+ 24 Kb5 Bd7+
  // Wait, let's use the explicit moves
  const mainInteractive = "9 Nxe5 Nc5 10 Bf3 Qxd1+ 11 Kxd1 Rd8+ 12 Kc2 Nfxe4 13 Nxe4 Bf5 14 Re1 Bxe5 15 fxe5 Rd4 16 Kc3 Rd3+ 17 Kc2 Rd4 18 Kc3 Rd3+ 19 Kb4 Na6+ 20 Ka5 b6+ 21 Kxa6 Bc8+ 22 Kb5 Bd7+ 23 Ka6 Bc8+ 24 Kb5 Bd7+";
  playMoves(chess, mainInteractive);
  console.log("Main line played successfully. FEN:", chess.fen());

  // Test Sideline A (8 fxe5)
  console.log("\nTesting Sideline A (8 fxe5)...");
  const chessA = new Chess();
  playMoves(chessA, "1 d4 Nf6 2 c4 g6 3 Nc3 Bg7 4 e4 d6 5 f4 O-O 6 Nf3 Na6 7 Be2 e5 8 fxe5 dxe5 9 Nxe5 c5!");
  const fenA = chessA.fen();
  
  // A1: 10 d5 Nxe4
  console.log("Testing Sideline A1...");
  const chessA1 = new Chess(fenA);
  playMoves(chessA1, "10 d5 Nxe4");
  console.log("Sideline A1 successful.");

  // A2: 10 Be3 cxd4 11 Bxd4 Qe7
  console.log("Testing Sideline A2...");
  const chessA2 = new Chess(fenA);
  playMoves(chessA2, "10 Be3 cxd4 11 Bxd4 Qe7");
  console.log("Sideline A2 successful.");

  // Test Sideline B (9 d5 after 8 fxe5 dxe5)
  console.log("\nTesting Sideline B (9 d5)...");
  const chessB = new Chess();
  playMoves(chessB, "1 d4 Nf6 2 c4 g6 3 Nc3 Bg7 4 e4 d6 5 f4 O-O 6 Nf3 Na6 7 Be2 e5 8 fxe5 dxe5 9 d5");
  console.log("Sideline B successful.");

  // Test Sideline C (10 Bg5 after 9 Nxe5 Nc5)
  console.log("\nTesting Sideline C (10 Bg5)...");
  const chessC = new Chess(fenAfter8);
  playMoves(chessC, "9 Nxe5 Nc5 10 Bg5 h6 11 Bxf6 Qxf6 12 b4 Na6 13 a3 c5");
  console.log("Sideline C successful.");

  // Test Sideline D (9 Qxd8 after 8 dxe5 dxe5)
  console.log("\nTesting Sideline D (9 Qxd8)...");
  const chessD = new Chess(fenAfter8);
  playMoves(chessD, "9 Qxd8 Rxd8 10 Nxe5 Nc5 11 Bf3 Be6");
  const fenD = chessD.fen();

  // D1: 12 Nd5 Nfd7
  console.log("Testing Sideline D1...");
  const chessD1 = new Chess(fenD);
  playMoves(chessD1, "12 Nd5 Nfd7 13 Nxd7 Rxd7 14 O-O c6 15 Ne3 Rd4 16 b3 Nxe4 17 Bb2 Nd2 18 Bxd2 Rxd2");
  console.log("Sideline D1 successful.");

  // D2: 12 O-O Nfd7
  console.log("Testing Sideline D2...");
  const chessD2 = new Chess(fenD);
  playMoves(chessD2, "12 O-O Nfd7 13 Nxd7 Bd4+ 14 Kh1 Rxd7 15 Nd5 c6 16 Be3 cxd5 17 Bxd4 dxe4 18 Bxc5 exf3 19 Rxf3 Bxc4");
  console.log("Sideline D2 successful.");

} catch (err: any) {
  console.error("ERROR:", err.message || err);
  process.exit(1);
}
