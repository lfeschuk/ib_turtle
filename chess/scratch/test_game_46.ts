import { Chess } from 'chess.js';

function testGame46() {
  const chess = new Chess();
  const initial = "d4 Nf6 c4 g6 Nf3 Bg7 g3 O-O Bg2 d6 O-O Nc6 Nc3 a6 h3 Rb8 e4 b5 e5 Nd7 cxb5 axb5 Ng5";
  
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
    "dxe5", "Bxc6", "exd4", "Nxb5", "Rb6", "Nxd4", "Nb8", "Nde6", "Qxd1", "Rxd1", 
    "Bxe6", "Nxe6", "fxe6", "Be4", "Bxb2", "Rb1", "Bxc1", "Rbxc1", "Na6", "Rd2", 
    "Rfb8", "Kf1", "Rd6", "Re2", "c5", "Rc3", "Rbb6", "Bd3", "Nb4", "Bc4", 
    "Kf7", "Rce3", "Kf6", "Rf3+", "Kg7", "Rfe3", "Kf6", "a4", "Nd5", "Rf3+", 
    "Kg7", "a5", "Rb7", "a6", "Ra7", "h4", "h5", "Re5", "Nb6", "Bxe6", 
    "Rxa6", "Rf7+", "Kh6", "Rxe7", "c4", "Rc5", "Ra1+", "Kg2", "Re1", 
    "Rcc7", "Rd7", "Rexd7", "Nxd7", "Bxd7", "Re7", "f4", "c3", "f5", 
    "Kh7", "f6", "Rf7", "Kf3", "Rxf6+", "Ke2", "Rf7", "Kd1", "Kh6", 
    "Kc2", "Rf3", "Rxc3", "Rf7", "Bc8", "Rf6", "Kd2", "g5", "hxg5+", 
    "Kxg5", "Rc5+", "Kg6", "Ke3", "h4", "g4", "h3", "Rh5", "Rb6", 
    "Bf5+", "Kg7", "Rxh3", "Rb3+", "Bd3"
  ];
  
  console.log("Playing main line moves...");
  for (let i = 0; i < mainLine.length; i++) {
    const m = mainLine[i];
    const player = i % 2 === 0 ? "B" : "W";
    const moveNum = 12 + Math.floor((i + 1) / 2);
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
  console.log("\nTesting sideline 12...Nxd4");
  const side1 = new Chess(fenAfterInitial);
  const side1Moves = ["Nxd4", "Qxd4", "Nxe5", "Qh4", "h6", "Nf3", "Nxf3+", "Bxf3", "e6", "Qxd8", "Rxd8", "a4"];
  for (const m of side1Moves) {
    if (!side1.move(m)) {
      console.error("Failed on side1 move:", m);
      return;
    }
  }
  console.log("Sideline 12...Nxd4 success!");

  console.log("\nTesting sideline 14 Ne2");
  const side2 = new Chess(fenAfterInitial);
  // play main line up to 13...exd4 (index 2)
  for (let i = 0; i <= 2; i++) side2.move(mainLine[i]);
  const side2Moves = ["Ne2", "h6", "Nf3", "e5"];
  for (const m of side2Moves) {
    if (!side2.move(m)) {
      console.error("Failed on side2 move:", m);
      return;
    }
  }
  console.log("Sideline 14 Ne2 success!");

  console.log("\nTesting sideline 15 Qf3");
  const side3 = new Chess(fenAfterInitial);
  for (let i = 0; i <= 4; i++) side3.move(mainLine[i]);
  if (!side3.move("Qf3") || !side3.move("Ne5")) {
    console.error("Failed on side3 moves");
    return;
  }
  console.log("Sideline 15 Qf3 success!");

  console.log("\nTesting sideline 15 Qc2");
  const side4 = new Chess(fenAfterInitial);
  for (let i = 0; i <= 4; i++) side4.move(mainLine[i]);
  const side4Moves = ["Qc2", "d3", "Qc4", "Ne5", "Qh4", "h6"]; // wait, 16...Ne5 is B's 16th move?
  // Let's trace: 14...Rb6 is index 4.
  // 15 Qc2 (W) 15...d3 (B) 16 Qc4 (W) 16...Ne5 (B) 17 Qh4 (W) 17...h6 (B).
  for (const m of side4Moves) {
    if (!side4.move(m)) {
      console.error("Failed on side4 move:", m);
      return;
    }
  }
  console.log("Sideline 15 Qc2 success!");

  console.log("\nTesting sideline 15 Bxd7");
  const side5 = new Chess(fenAfterInitial);
  for (let i = 0; i <= 4; i++) side5.move(mainLine[i]);
  const side5Moves = ["Bxd7", "Qxd7", "Na3", "h6"];
  for (const m of side5Moves) {
    if (!side5.move(m)) {
      console.error("Failed on side5 move:", m);
      return;
    }
  }
  console.log("Sideline 15 Bxd7 success!");

  console.log("\nTesting sideline 15 Na7 Branch A");
  const side6a = new Chess(fenAfterInitial);
  for (let i = 0; i <= 4; i++) side6a.move(mainLine[i]);
  const side6aMoves = ["Na7", "Nb8", "Nxc8", "Rxc6", "Na7", "Rb6"];
  for (const m of side6aMoves) {
    if (!side6a.move(m)) {
      console.error("Failed on side6a move:", m);
      return;
    }
  }
  console.log("Sideline 15 Na7 Branch A success!");

  console.log("\nTesting sideline 15 Na7 Branch B");
  const side6b = new Chess(fenAfterInitial);
  for (let i = 0; i <= 4; i++) side6b.move(mainLine[i]);
  const side6bMoves = ["Na7", "Nb8", "Bg2", "Bb7", "a4", "Bxg2", "Kxg2", "c6"];
  for (const m of side6bMoves) {
    if (!side6b.move(m)) {
      console.error("Failed on side6b move:", m);
      return;
    }
  }
  console.log("Sideline 15 Na7 Branch B success!");

  console.log("\nTesting sideline Salov-Kuzmin");
  const side7 = new Chess(fenAfterInitial);
  for (let i = 0; i <= 12; i++) side7.move(mainLine[i]);
  const side7Moves = ["Bg2", "Bxb2", "Rb1", "Bd4", "Be3", "Bxe3", "fxe3", "Nd7", "Rxb6"];
  for (const m of side7Moves) {
    if (!side7.move(m)) {
      console.error("Failed on side7 move:", m);
      return;
    }
  }
  console.log("Sideline Salov-Kuzmin success!");
}

testGame46();
