import { Chess } from 'chess.js';

function testMove(move: string) {
  const chess = new Chess();
  const prepMoves = [
    'd4', 'Nf6', 'c4', 'g6', 'Nc3', 'Bg7', 'e4', 'd6', 'f3', 'O-O',
    'Bg5', 'c5', 'd5', 'e6', 'Qd2', 'exd5', 'Nxd5', 'Be6', 'Ne2', 'Nc6',
    'Nec3', 'Bxd5', 'Nxd5', 'h6', 'Bxh6'
  ];

  for (const m of prepMoves) {
    chess.move(m);
  }

  console.log(`\nPosition before Black's move (after Bxh6):`);
  console.log(chess.ascii());

  console.log(`Testing Black move: ${move}`);
  try {
    const result = chess.move(move);
    if (result) {
      console.log(`  Move ${move} is LEGAL.`);
      console.log(`  Board after ${move}:`);
      console.log(chess.ascii());
      
      // Try White's response
      if (move === 'Nxe4') {
        console.log("  Trying White response: fxe4");
        try {
          const r2 = chess.move('fxe4');
          if (r2) {
             console.log("    fxe4 is LEGAL.");
             console.log(chess.ascii());
             console.log("    Trying Black response: Qh4+");
             try {
               const r3 = chess.move('Qh4+');
               if (r3) {
                 console.log("      Qh4+ is LEGAL.");
                 console.log(chess.ascii());
               }
             } catch (e: any) {
               console.log(`      Qh4+ is ILLEGAL: ${e.message}`);
             }
          }
        } catch (e: any) {
          console.log(`    fxe4 is ILLEGAL: ${e.message}`);
        }
      } else if (move === 'Nxd5') {
         // In the sideline: 14 exd5 Qh4+ 15 g3 Qxh6
         console.log("  Trying White response: exd5");
         try {
           const r2 = chess.move('exd5');
           if (r2) {
              console.log("    exd5 is LEGAL.");
              console.log(chess.ascii());
              console.log("    Trying Black response: Qh4+");
              try {
                const r3 = chess.move('Qh4+');
                if (r3) {
                  console.log("      Qh4+ is LEGAL.");
                  console.log(chess.ascii());
                }
              } catch (e: any) {
                console.log(`      Qh4+ is ILLEGAL: ${e.message}`);
              }
           }
         } catch (e: any) {
           console.log(`    exd5 is ILLEGAL: ${e.message}`);
         }
      }
    } else {
      console.log(`  Move ${move} is ILLEGAL.`);
    }
  } catch (e: any) {
    console.log(`  Error testing ${move}: ${e.message}`);
  }
}

testMove('Nxe4');
testMove('Nxd5');
