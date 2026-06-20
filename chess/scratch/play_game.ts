import { Chess } from 'chess.js';

const chess = new Chess();

const movesStr = "1. d4 Nf6 2. c4 g6 3. Nc3 Bg7 4. e4 d6 5. Be2 O-O 6. Bg5 Na6 7. Qd2 e5 8. d5 c6 9. f3 cxd5 10. cxd5 Bd7 11. h4 Qa5 12. g4 h5 13. Bxf6 Bxf6 14. gxh5 Kg7 15. hxg6 fxg6 16. h5 Rh8 17. h6+ Kh7 18. Nh3 Bxh3 19. Rxh3 Rac8 20. Kf1 Nc5 21. Rb1 Qd8 22. Kg2 Bg5 23. Qe1 Nd7 24. Qg3 Bf4 25. Qg4 Re8 26. Kh1 Nf6 27. Qg2 Rg8 28. Bd3 Qd7 29. Bb5 Qf7 30. Bd3 g5 31. Ne2 Rg6 32. Qf2 a6 33. Ng3 Bxg3 34. Qxg3 Rxh6 35. Rg1 Rxh3+ 36. Qxh3+ Qh5 37. Qxh5+ Nxh5 38. Rg2 Nf4 39. Rc2 Rxc2 40. Bxc2 Kg6 41. Kg1 Kh5 42. Kf2 Kh4 43. b4 b6 44. a3 Kh3 45. Ba4 Kh2 46. Bd7 Nh3+ 47. Ke3 Kg2 48. Bc8 a5 49. bxa5 bxa5 50. Bf5 Nf2 51. Bd7 Kg3 52. Bc8 Nd1+ 53. Kd2 Nf2 54. Ke3 Nd1+ 55. Kd2 Nb2 56. Ke2 Nc4 57. Ba6 Nb6 58. Ke3 Nd7 59. Bb5 Nf6 60. Be2 Nh5 61. Bb5 Nf4 62. Be8 Ng2+ 63. Ke2 Kf4 64. Bd7 Ne3 65. Ba4 g4 66. fxg4 Nxg4 67. Kd3 Kf3 68. Bd1+ Kf4 69. Bc2 Nf6 70. Kc4 Nxe4 71. Kb5 Nc3+ 72. Kxa5 e4 73. Kb4 Nxd5+ 74. Kc4 Ne3+ 75. Kc3 Nxc2 76. Kxc2 Kf3 77. a4 e3 78. a5 e2 79. a6 e1=Q 80. a7 Qe4+ 81. Kb3";

const moves = movesStr.trim().split(/\s+/).filter(Boolean);

let failed = false;
for (let i = 0; i < moves.length; i++) {
  const move = moves[i];
  if (/^\d+\.?$/.test(move)) continue;
  const cleaned = move.replace(/[!?+#=]+/g, '');
  try {
    console.log(`Playing index ${i}: ${move} (cleaned: ${cleaned})`);
    if (i === 65) {
      console.log("Board before index 65 (Bg5):\n" + chess.ascii());
    }
    if (i === 85) {
      console.log("Board before index 85 (Bb5):\n" + chess.ascii());
    }
    if (!chess.move(cleaned)) {
      console.error(`chess.js returned null for move ${move} at index ${i}`);
      failed = true;
      break;
    }
  } catch (err: any) {
    console.error(`Error playing move ${move} at index ${i}:`, err.message || err);
    failed = true;
    break;
  }
}

if (!failed) {
  console.log("Game played successfully up to move 80!");
  console.log(chess.ascii());
} else {
  console.log("ASCII board before error:\n" + chess.ascii());
}
