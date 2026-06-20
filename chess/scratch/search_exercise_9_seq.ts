import { Chess } from 'chess.js';

const chess = new Chess();

// Try to play the sequence
const seq = [
  'd4', 'Nf6', 'c4', 'g6', 'Nc3', 'Bg7', 'e4', 'd6', 'Nf3', 'O-O',
  'Be2', 'e5', 'O-O', 'Nbd7', 'Be3', 'Re8', 'd5', 'Nc5',
  'Nd2', 'a6',
  'Qc2', 'Rb8',
  'b4', 'Ncxe4', 'Ndxe4', 'Nxe4', 'Qxe4', 'Bf5', 'Qf3', 'e4'
];

let failed = false;
for (let i = 0; i < seq.length; i++) {
  const m = seq[i];
  try {
    // We need to clean the move string if it has annotations, but here we use SAN
    // chess.js move() accepts SAN
    // For captures like 'Nd2xe4' we might need to specify the source or just 'Nxe4' if it is unambiguous.
    // In our case, if White has Knight on d2 and Knight on c3.
    // If Black Knight is on e4 (after Ncxe4).
    // White Knight on d2 can capture: Nxe4 (or Nde4).
    // White Knight on c3 can capture: Nxe4 (or Nce4).
    // If we want d2 Knight to capture, we should use 'Nde4' or 'Nd2xe4' (standard SAN is Nde4).
    // Let's use 'Nde4' instead of 'Nd2xe4' in the sequence.
    let moveStr = m;
    if (m === 'Nd2xe4') moveStr = 'Nde4';
    
    const result = chess.move(moveStr);
    if (result) {
      console.log(`${i+1}: ${m} -> ${result.san} OK`);
    } else {
      console.error(`${i+1}: ${m} FAILED: returned null`);
      failed = true;
      break;
    }
  } catch (e: any) {
    console.error(`${i+1}: ${m} FAILED: ${e.message}`);
    failed = true;
    break;
  }
}

if (!failed) {
  console.log("SUCCESS!");
  console.log(chess.ascii());
} else {
  console.log("FAILED");
}
