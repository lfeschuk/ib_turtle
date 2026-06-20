import { Chess } from 'chess.js';

const chess = new Chess();
// Initial moves of Game 55
const initial = "1 d4 Nf6 2 c4 g6 3 Nc3 Bg7 4 e4 d6 5 Be2 O-O 6 Bg5 h6 7 Be3 c5!?";
const moves = initial.trim().split(/\s+/).filter(Boolean);

for (const m of moves) {
    if (/^\d+\.?$/.test(m)) continue;
    const cleaned = m.replace(/[!?]+/g, '');
    chess.move(cleaned);
}
console.log("Initial state FEN:", chess.fen());

// Try the sideline: 8 e5 dxe5 9 Qxd8 Rxd8 10 Rd1 Rxd1+ 11 Bxd1 Ng4 12 Bxc5 Nxe5 13 Nd5 Nbc6
const sideline = [
    "dxc5", "Qa5",
    "Qd2", "dxc5",
    "Bxh6", "Rd8",
    "Qe3", "Bxh6",
    "Qxh6", "Nxe4",
    "Rc1", "Nc6"
];

for (const m of sideline) {
    try {
        chess.move(m);
        console.log(`Played ${m}, FEN: ${chess.fen()}`);
    } catch (err: any) {
        console.error(`Failed on ${m}:`, err.message);
        break;
    }
}
