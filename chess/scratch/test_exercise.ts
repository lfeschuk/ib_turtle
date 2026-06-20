import { Chess } from 'chess.js';

const chess = new Chess();

// 1 Nf3 Nf6 2 c4 g6 3 d4 Bg7 4 Nc3 O-O 5 g3 d6 6 Bg2 Nbd7 7 O-O e5 8 e4 c6 9 h3 Qa5
// 10 Re1 exd4 11 Nxd4 Ne5 12 Bf1 Re8 13 Be3 Be6 14 Nxe6 Rxe6 15 Rb1
const moves = [
  "Nf3", "Nf6", "c4", "g6", "d4", "Bg7", "Nc3", "O-O", "g3", "d6", 
  "Bg2", "Nbd7", "O-O", "e5", "e4", "c6", "h3", "Qa5",
  "Re1", "exd4", "Nxd4", "Ne5", "Bf1", "Re8", "Be3", "Be6",
  "Nxe6", "Rxe6", "Rb1"
];

for (const m of moves) {
  chess.move(m);
}

console.log("Position before Exercise 7:");
console.log(chess.ascii());

// Try 15...Nxe4
try {
  chess.move("Nxe4");
  console.log("15...Nxe4 is legal.");
  console.log(chess.ascii());
  
  // White plays 16 Nxe4
  chess.move("Nxe4");
  console.log("16 Nxe4 is legal.");
  
  // Black plays 16...Qxe1
  chess.move("Qxe1");
  console.log("16...Qxe1 is legal.");
  
  // White plays 17 Qxe1
  chess.move("Qxe1");
  console.log("17 Qxe1 is legal.");
  
  // Black plays 17...Nf3+
  chess.move("Nf3+");
  console.log("17...Nf3+ is legal.");
  console.log(chess.ascii());
  
  // White plays 18 Kh1
  chess.move("Kh1");
  
  // Black plays 18...Nxe1
  chess.move("Nxe1");
  console.log("18...Nxe1 is legal.");
  
  // White plays 19 Rxe1
  chess.move("Rxe1");
  console.log("Position after combination:");
  console.log(chess.ascii());
  
} catch (e: any) {
  console.error("Failed:", e.message);
}
