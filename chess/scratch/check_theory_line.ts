import { Chess } from 'chess.js';

function cleanMoveStr(m: string): string {
  return m.replace(/[!?+#=]+/g, '');
}

function playMoves(chess: Chess, moves: string[]) {
  for (const move of moves) {
    const cleaned = cleanMoveStr(move);
    if (!chess.move(cleaned)) {
      throw new Error(`Invalid move: ${move}`);
    }
  }
}

const initialMoves = [
  "d4", "Nf6", "c4", "g6", "Nc3", "Bg7", "e4", "d6", "f4", "O-O",
  "Nf3", "Na6", "Bd3", "e5"
];

// Corrected Sideline 1: 9. Be2 (instead of 9. Qxd8)
const sideline1_corrected = [
  "Be2", "Qxd1+", "Bxd1", "Rd8", "Nxe5", "Nc5", "Bf3", "Be6"
];

// Sub-sideline 1a (from 12...Be6, which is index 7 in sideline1_corrected)
// Note: move numbers will be shifted by 1
// Book: 12. Nd5 Nfd7 13. Nxd7 Rxd7 14. O-O c6 15. Ne3 Rd4 16. b3 Nxe4 17. Bb2 Nd2
// Corrected: 13. Nd5 Nfd7 14. Nxd7 Rxd7 15. O-O c6 16. Ne3 Rd4 17. b3 Nxe4 18. Bb2 Nd2
const sideline1a_corrected = [
  "Nd5", "Nfd7", "Nxd7", "Rxd7", "O-O", "c6", "Ne3", "Rd4", "b3", "Nxe4", "Bb2", "Nd2"
];

const sideline1a_sub_corrected = [
  "Nxc7", "Nxe5", "fxe5", "Nd3+", "Kf1", "Bxc4"
];

// Sub-sideline 1b (from 12...Be6)
// Book: 12. O-O Nfd7 13. Nxd7 Bd4+ 14. Kh1 Rxd7 15. Nd5 c6 16. Be3 cxd5 17. Bxd4 dxe4 18. Bxc5 exf3 19. Rxf3 Bxc4
// Corrected: 13. O-O Nfd7 14. Nxd7 Bd4+ 15. Kh1 Rxd7 16. Nd5 c6 17. Be3 cxd5 18. Bxd4 dxe4 19. Bxc5 exf3 20. Rxf3 tactics...
const sideline1b_corrected = [
  "O-O", "Nfd7", "Nxd7", "Bd4+", "Kh1", "Rxd7", "Nd5", "c6", "Be3", "cxd5", "Bxd4", "dxe4", "Bxc5", "exf3", "Rxf3", "Bxc4"
];

const s1Chess = new Chess();
playMoves(s1Chess, initialMoves);
playMoves(s1Chess, ["dxe5", "dxe5"]); // Play 8. dxe5 dxe5
console.log("Playing corrected Sideline 1...");
playMoves(s1Chess, sideline1_corrected);
console.log("Corrected Sideline 1 OK. FEN: " + s1Chess.fen());

console.log("Playing corrected Sideline 1a...");
const s1aChess = new Chess();
playMoves(s1aChess, initialMoves);
playMoves(s1aChess, ["dxe5", "dxe5"]);
playMoves(s1aChess, sideline1_corrected);
playMoves(s1aChess, sideline1a_corrected);
console.log("Corrected Sideline 1a OK.");

console.log("Playing corrected Sideline 1a sub...");
const s1aSubChess = new Chess();
playMoves(s1aSubChess, initialMoves);
playMoves(s1aSubChess, ["dxe5", "dxe5"]);
playMoves(s1aSubChess, sideline1_corrected);
playMoves(s1aSubChess, ["Nd5", "Nfd7"]); // 13. Nd5 Nfd7
playMoves(s1aSubChess, sideline1a_sub_corrected);
console.log("Corrected Sideline 1a sub OK.");

console.log("Playing corrected Sideline 1b...");
const s1bChess = new Chess();
playMoves(s1bChess, initialMoves);
playMoves(s1bChess, ["dxe5", "dxe5"]);
playMoves(s1bChess, sideline1_corrected);
playMoves(s1bChess, sideline1b_corrected);
console.log("Corrected Sideline 1b OK.");
