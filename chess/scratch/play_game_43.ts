import { Chess } from 'chess.js';

const chess = new Chess();

const moves = [
  "Nf3", "Nf6", "c4", "g6", "d4", "Bg7", "Nc3", "O-O", "g3", "d6", 
  "Bg2", "Nbd7", "O-O", "e5", "e4", "a6", "h3", "b5",
  "cxb5", "axb5", "b4", "c5", "bxc5", "b4", "Ne2", "Bb7",
  "cxd6", "Nxe4", "dxe5", "Nxe5", "Nxe5", "Bxe5", "Bh6", "Re8",
  "Rb1", "Qxd6", "Qb3", "Nd2", "Bxd2", "Bxg2", "Kxg2", "Qxd2",
  "Nc1", "Ra3", "Nd3", "Rxb3", "Rxb3", "Bc3"
];

let idx = 0;
for (const m of moves) {
  try {
    chess.move(m);
    console.log(`Step ${idx} (${m}) success`);
    idx++;
  } catch (e: any) {
    console.error(`Failed at step ${idx} (${m}): ${e.message}`);
    console.log(chess.ascii());
    break;
  }
}

if (idx === moves.length) {
  console.log("Game played successfully!");
  console.log(chess.ascii());
}
