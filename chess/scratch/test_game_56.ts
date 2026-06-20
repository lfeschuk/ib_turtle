import { Chess } from 'chess.js';

const chess = new Chess();
// Initial moves of Game 56
const initial = "1 d4 Nf6 2 c4 g6 3 Nc3 Bg7 4 e4 d6 5 Be2 O-O 6 Bg5 c5 7 d5 h6 8 Bf4 e6 9 dxe6 Bxe6 10 Bxd6 Re8 11 Nf3 Nc6 12 O-O";
const moves = initial.trim().split(/\s+/).filter(Boolean);

for (const m of moves) {
    if (/^\d+\.?$/.test(m)) continue;
    const cleaned = m.replace(/[!?]+/g, '');
    chess.move(cleaned);
}
console.log("Initial state FEN:", chess.fen());

// Main line up to 26...Rb2!
const mainLine = [
    "Nd4", "e5", "Nd7", "Nxd4", "cxd4", "Qxd4", "Nxe5", "Bxe5", "Qxd4", "Bxd4", "Bxd4",
    "Rac1", "Rad8", "b3", "Bxc3", "Rxc3", "Rd2", "Bf3", "Rxa2", "Bxb7", "Rb8", "Be4", "Ra3",
    "Bc2", "a5", "Re3", "Ra2", "Bxg6", "Rb2"
];

for (const m of mainLine) {
    try {
        chess.move(m.replace(/[!?]+/g, ''));
        console.log(`Played main: ${m}, FEN: ${chess.fen()}`);
    } catch (err: any) {
        console.error(`Failed on main ${m}:`, err.message);
        process.exit(1);
    }
}

// Sideline: 27 Rb1 Rxb1 28 Bxb1 a4 29 Ba2 Rd8 30 Kf1 Rd1+ 31 Re1 Rd2 32 Ra1 axb3 33 Bxb3 Rb2 34 Ra8+ Kg7 35 Ba2 Rc2 36 Ra4 Bd7 37 Ra8 Be6
const sideline = [
    "Rb1", "Rxb1", "Bxb1", "a4", "Ba2", "Rd8", "Kf1", "Rd1+", "Re1", "Rd2", "Ra1", "axb3",
    "Bxb3", "Rb2", "Ra8+", "Kg7", "Ba2", "Rc2", "Ra4", "Bd7", "Ra8", "Be6"
];

for (const m of sideline) {
    try {
        chess.move(m.replace(/[!?]+/g, ''));
        console.log(`Played side: ${m}, FEN: ${chess.fen()}`);
    } catch (err: any) {
        console.error(`Failed on side ${m}:`, err.message);
        break;
    }
}
