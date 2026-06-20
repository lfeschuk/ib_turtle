import { Chess } from 'chess.js';

function testGame47() {
  const chess = new Chess();
  const initial = "d4 Nf6 c4 g6 Nc3 Bg7 e4 d6 f4 O-O Nf3 c5 d5 e6 Be2 exd5 cxd5";
  
  console.log("Playing initial moves...");
  for (const m of initial.split(/\s+/)) {
    if (!chess.move(m)) {
      console.error("Failed on initial move:", m);
      return;
    }
  }
  
  console.log("Initial moves successful. FEN:", chess.fen());
  const fenAfterInitial = chess.fen();
  
  const mainLine = [
    "Bg4", "O-O", "Nbd7", "Re1", "Re8", "h3", "Bxf3", "Bxf3", "Qa5!",
    "Be3", "b5", "a3", "Nb6", "e5", "Nc4", "exf6", "Nxe3", "Rxe3", "Rxe3", "fxg7", "Rae8",
    "f5", "b4", "axb4", "Qxb4", "Qd2", "Qh4", "fxg6", "hxg6", "Rf1", "a6", "Nd1", "R3e5",
    "Nf2", "f5", "Bd1", "Kxg7", "Qa5", "Rxd5", "Bf3", "Rd4", "Qxa6", "Rd2", "Bc6",
    "Re1", "Qb7+", "Kh6", "Ng4+", "fxg4", "Qf7", "Rxf1+", "Qxf1", "Kg7"
  ];
  
  console.log("Playing main line moves...");
  for (let i = 0; i < mainLine.length; i++) {
    const m = mainLine[i].replace(/[!?+#=]+/g, '');
    const player = i % 2 === 0 ? "B" : "W";
    const moveNum = 9 + Math.floor((i + 1) / 2);
    try {
      if (!chess.move(m)) {
        console.error(`Failed on main move ${moveNum}${player}: ${m}`);
        console.log(chess.ascii());
        return;
      }
    } catch (err: any) {
      console.error(`Error on main move ${moveNum}${player}: ${m}`, err.message);
      return;
    }
  }
  console.log("Main line success! FEN:", chess.fen());

  // Test sidelines
  console.log("\nTesting sideline 10 e5");
  const side1 = new Chess(fenAfterInitial);
  // play 9...Bg4 (index 0)
  side1.move("Bg4");
  const side1Moves = ["e5", "dxe5", "fxe5", "Nfd7", "e6", "Bxf3", "Bxf3", "Ne5"];
  for (const m of side1Moves) {
    if (!side1.move(m)) {
      console.error("Failed on side1 move:", m);
      return;
    }
  }
  console.log("Sideline 10 e5 success!");

  console.log("\nTesting sideline 11...h6 & 13 g4");
  const side2 = new Chess(fenAfterInitial);
  // play up to 10...Nbd7 (index 2)
  for (let i = 0; i <= 2; i++) side2.move(mainLine[i].replace(/[!?]+/g, ''));
  const side2Moves = ["h3", "Bxf3", "Bxf3", "Re8", "g4", "h6", "h4", "h5"];
  for (const m of side2Moves) {
    if (!side2.move(m)) {
      console.error("Failed on side2 move:", m);
      return;
    }
  }
  console.log("Sideline 11...h6 & 13 g4 success!");

  console.log("\nTesting sideline 14 a4");
  const side3 = new Chess(fenAfterInitial);
  for (let i = 0; i <= 8; i++) side3.move(mainLine[i].replace(/[!?]+/g, ''));
  const side3Moves = ["a4", "c4", "Be3", "Nc5", "Bxc5", "Qxc5", "Kh1", "Nd7"];
  // Wait, does it say 16...Nd7 or 16...Rfd8?
  // Text: "14 a4 to stop ...b7-b5 but after 14...c4! 15 Be3 Nc5 16 Bxc5 ... 16...Qxc5+ 17 Kh1 Nd7!"
  // Wait, 14 a4 (White 14), 14...c4 (Black 14), 15 Be3 (White 15), 15...Nc5 (Black 15), 16 Bxc5 (White 16), 16...Qxc5+ (Black 16), 17 Kh1 (White 17), 17...Nd7! (Black 17).
  for (const m of side3Moves) {
    if (!side3.move(m.replace(/[!?+]+/g, ''))) {
      console.error("Failed on side3 move:", m);
      return;
    }
  }
  console.log("Sideline 14 a4 success!");

  console.log("\nTesting sideline 16 Bf2");
  const side4 = new Chess(fenAfterInitial);
  for (let i = 0; i <= 11; i++) side4.move(mainLine[i].replace(/[!?]+/g, '')); // up to 15 a3
  // Wait, the main line goes:
  // 14 Be3 (index 9), 14...b5 (index 10), 15 a3 (index 11), 15...Nb6! (index 12), 16 e5 (index 13).
  // The alternative is at White's 16th move: "16 Bf2 is an important alternative... Kozul-Nunn... 16...Nc4 17 Qc2 Nd7 18 Be2 Rab8 19 a4 b4".
  // So we play up to 15...Nb6! (index 12).
  const side4Moves = ["Bf2", "Nc4", "Qc2", "Nd7", "Be2", "Rab8", "a4", "b4"];
  // Wait, does Kozul-Nunn continue?
  // "20 Bxc4? bxc3 21 b3 a6! 22 Rec1 Nb6 23 Bf1 c4! 24 Bxc4 Nxc4 25 bxc4 Rb2"
  const side4MovesCont1 = ["Bxc4", "bxc3", "b3", "a6", "Rec1", "Nb6", "Bf1", "c4", "Bxc4", "Nxc4", "bxc4", "Rb2"];
  // Vaisser's line: "Instead of 20 Bxc4 he gives 20 Nb5! Nxb2 21 Nxd6 b3 22 Qb1 Nxa4 23 Ra3!"
  const side4MovesCont2 = ["Nb5", "Nxb2", "Nxd6", "b3", "Qb1", "Nxa4", "Ra3"];

  const side4a = new Chess(fenAfterInitial);
  for (let i = 0; i <= 12; i++) side4a.move(mainLine[i].replace(/[!?]+/g, ''));
  for (const m of [...side4Moves, ...side4MovesCont1]) {
    if (!side4a.move(m.replace(/[!?]+/g, ''))) {
      console.error("Failed on side4a move:", m);
      return;
    }
  }
  console.log("Sideline 16 Bf2 (Kozul-Nunn) success!");

  const side4b = new Chess(fenAfterInitial);
  for (let i = 0; i <= 12; i++) side4b.move(mainLine[i].replace(/[!?]+/g, ''));
  for (const m of [...side4Moves, ...side4MovesCont2]) {
    if (!side4b.move(m.replace(/[!?]+/g, ''))) {
      console.error("Failed on side4b move:", m);
      return;
    }
  }
  console.log("Sideline 16 Bf2 (Vaisser) success!");
}

testGame47();
