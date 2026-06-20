import { ChessMove } from './types';

export const OPEN_SETUP_MAP: Record<string, ChessMove[]> = {
  "exercise_1": [
    { move_number: 1, player: 'W', move: "d4", commentary: "White begins by pushing the queen's pawn. This controls key central squares, unlocks the dark-squared bishop, and keeps the king safe compared to e4." },
    { move_number: 1, player: 'B', move: "Nf6", commentary: "Black develops the knight to f6, blocking an immediate e4 push by White and keeping options open. This is the hypermodern signature entry, choosing control via pieces." },
    { move_number: 2, player: 'W', move: "c4", commentary: "White grabs queenside space and supports the central d4 pawn, preparing Nc3 while reinforcing control of d5." },
    { move_number: 2, player: 'B', move: "g6", commentary: "The signature King's Indian move! Black prepares to placing the bishop on the long diagonal (fianchetto) to control the center from a distance." },
    { move_number: 3, player: 'W', move: "Nc3", commentary: "White develops the knight to its natural post on c3, aiming direct pressure at the critical d5 and e4 squares." },
    { move_number: 3, player: 'B', move: "Bg7", commentary: "Black completes the fianchetto! From g7, the bishop acts as a sniper on the long diagonal, defending the king and targeting d4." },
    { move_number: 4, player: 'W', move: "e4", commentary: "White establishes a classical broad pawn center in the middle (c4-d4-e4). Black allows this by design, waiting for White to overextend." },
    { move_number: 4, player: 'B', move: "d6", commentary: "Black stops the e4 pawn from pushing further to e5. It solidifies the e5 square, paving the path to strike back with ...e5 or ...c5." },
    { move_number: 5, player: 'W', move: "Nf3", commentary: "White develops the king's knight to f3, reinforcing the d4 center and preparing kingside castling." },
    { move_number: 5, player: 'B', move: "O-O", commentary: "Black castles to safety. The king fits perfectly inside the solid triple-pawn and bishop bunker on g7." },
    { move_number: 6, player: 'W', move: "Be2", commentary: "White develops the light-squared bishop. Be2 is a solid, classical choice, preparing to castle and avoiding tactical complications." },
    { move_number: 6, player: 'B', move: "e5", commentary: "The crucial counter-strike! Black strikes directly at White's centerpiece. This defines the Classical King's Indian Defence." },
    { move_number: 7, player: 'W', move: "dxe5", commentary: "The Exchange Variation! White opts for a lower-risk, grinding endgame by trading center pawns immediately." },
    { move_number: 7, player: 'B', move: "dxe5", commentary: "Black recaptures the pawn on e5. Note that the d-file is now completely open." },
    { move_number: 8, player: 'W', move: "Qxd8", commentary: "White trades off queens. By exchanging queens, White deflates Black's dynamic attacking chances on the kingside." },
    { move_number: 8, player: 'B', move: "Rxd8", commentary: "Black recaptures with the rook, grasping active control of the open d-file with tempo." },
    { move_number: 9, player: 'W', move: "Bg5", commentary: "The crucial pin! White pins the f6 knight against the d8 rook, preparing to overload Black's center defender." },
    { move_number: 9, player: 'B', move: "Re8", commentary: "Black simply steps the rook aside to release the pin. Now we are set up perfectly to begin the active puzzle!" }
  ],
  "exercise_2": [
    { move_number: 1, player: 'W', move: "d4", commentary: "White claims central space by advancing the queen's pawn." },
    { move_number: 1, player: 'B', move: "Nf6", commentary: "Black developing the knight in hypermodern style to keep White's e4 pawn back." },
    { move_number: 2, player: 'W', move: "c4", commentary: "White claims queenside space, preparing Nc3 and eyeing d5." },
    { move_number: 2, player: 'B', move: "g6", commentary: "Black initiates the King's Indian bishop fianchetto track." },
    { move_number: 3, player: 'W', move: "Nc3", commentary: "Developing the knight to its most active square, aiming eyes on e4." },
    { move_number: 3, player: 'B', move: "Bg7", commentary: "Black places the bishop on the long diagonal, preparing kingside defense." },
    { move_number: 4, player: 'W', move: "e4", commentary: "White takes central control with a broad pawn front." },
    { move_number: 4, player: 'B', move: "d6", commentary: "Black stops the e4 pawn from pushing further and secures the e5 counter-threat." },
    { move_number: 5, player: 'W', move: "f3", commentary: "The signature of the Sämisch Variation! White solidifies the e4 pawn and prepares to block the f6 knight's influence." },
    { move_number: 5, player: 'B', move: "O-O", commentary: "Black castles to absolute safety, securing the king first." },
    { move_number: 6, player: 'W', move: "Be3", commentary: "White develops the dark-squared bishop, reinforcing d4 and preparing a potential Qd2+Bh6 battery to trade dark bishops." },
    { move_number: 6, player: 'B', move: "e5", commentary: "Black strikes at the center. Despite 5.f3, Black insists on the classical break." },
    { move_number: 7, player: 'W', move: "Nge2", commentary: "White develops the knight to e2 instead of f3, keeping the f-pawn and bishop's action open." },
    { move_number: 7, player: 'B', move: "c6", commentary: "Black reinforces the center and prepares an eventual queenside expansion with ...b5 or ...d5." },
    { move_number: 8, player: 'W', move: "Qd2", commentary: "White sets up the Qd2-Be3 battery, planning to castle queenside and launch a kingside storm." },
    { move_number: 8, player: 'B', move: "Nbd7", commentary: "Black develops the knight to d7, pointing eyes at c5 and reinforcing the e5 pawn." },
    { move_number: 9, player: 'W', move: "Rd1", commentary: "White prepares against queenside break attempts by positioning a rook on the d-file." },
    { move_number: 9, player: 'B', move: "a6", commentary: "Black claims queenside space with ...a6, preparing a eventual push of the b-pawn." },
    { move_number: 10, player: 'W', move: "dxe5", commentary: "White decides to trade on e5, opening the file to seek tactical avenues." },
    { move_number: 10, player: 'B', move: "dxe5", commentary: "Black recaptures, maintaining active central structure." },
    { move_number: 11, player: 'W', move: "Nc1", commentary: "White repositions the knight, intending to anchor it on b3 or d3 to squeeze Black's queenside." },
    { move_number: 11, player: 'B', move: "Nh5", commentary: "Black jumps the knight to h5, freeing the f-pawn and preparing kingside piece activity." },
    { move_number: 12, player: 'W', move: "g3", commentary: "White plays g3 to stop ...Nf4 jumps from Black." },
    { move_number: 12, player: 'B', move: "Qe7", commentary: "Black develops the queen to e7, coordinating pieces and preparing for deep tactical work." }
  ],
  "exercise_3": [
    { move_number: 1, player: 'W', move: "d4", commentary: "White occupies the d4 square." },
    { move_number: 1, player: 'B', move: "Nf6", commentary: "Black develops the knight to f6." },
    { move_number: 2, player: 'W', move: "c4", commentary: "White builds c4 for queenside presence." },
    { move_number: 2, player: 'B', move: "g6", commentary: "Black moves g6, aiming for the fianchetto." },
    { move_number: 3, player: 'W', move: "Nc3", commentary: "White develops the queen's knight." },
    { move_number: 3, player: 'B', move: "Bg7", commentary: "Black's bishop takes its sniper post." },
    { move_number: 4, player: 'W', move: "e4", commentary: "White grabs the center with e4." },
    { move_number: 4, player: 'B', move: "d6", commentary: "Black controls the center from a distance." },
    { move_number: 5, player: 'W', move: "Nf3", commentary: "White develops the knight to f3, solidifying control." },
    { move_number: 5, player: 'B', move: "O-O", commentary: "Black castles his king into safety." },
    { move_number: 6, player: 'W', move: "Be2", commentary: "White plays Be2 solidly." },
    { move_number: 6, player: 'B', move: "e5", commentary: "Black performs the classical dynamic counter-thrust." },
    { move_number: 7, player: 'W', move: "O-O", commentary: "White castles. Now we enter the Classical Main Line." },
    { move_number: 7, player: 'B', move: "Nc6", commentary: "Black develops the knight to c6, placing maximum pressure on d4." },
    { move_number: 8, player: 'W', move: "d5", commentary: "White steps forward to shut down the knight, closing the center." },
    { move_number: 8, player: 'B', move: "Ne7", commentary: "Black's knight is forced to retreat. It will recycle toward the kingside attack." },
    { move_number: 9, player: 'W', move: "Nd2", commentary: "White retreats the knight to d2, preparing the queenside pawn expansion c4-c5." },
    { move_number: 9, player: 'B', move: "a5", commentary: "Black plays ...a5 to stop White's initial b4 queenside march." },
    { move_number: 10, player: 'W', move: "a3", commentary: "White prepares to support b4 anyway with a3 and Rb1." },
    { move_number: 10, player: 'B', move: "Nd7", commentary: "Black recycles the knight to d7, freeing the f7-f5 pawn storm." },
    { move_number: 11, player: 'W', move: "Rb1", commentary: "White supports b4 queenside play." },
    { move_number: 11, player: 'B', move: "f5", commentary: "Black starts the historic kingside pawn storm with ...f5!" },
    { move_number: 12, player: 'W', move: "b4", commentary: "White launches the b4 strike! A race of wings begins." },
    { move_number: 12, player: 'B', move: "Kh8", commentary: "Black tucks the king to h8, stepping out of any potential g8-a7 diagonal complications." },
    { move_number: 13, player: 'W', move: "f3", commentary: "White reinforces e4 in anticipation of Black's ...f4 kingside lock." },
    { move_number: 13, player: 'B', move: "Ng8", commentary: "Black recycles the e7 knight to g8, preparing to target the h6/f6 sectors." },
    { move_number: 14, player: 'W', move: "c5", commentary: "White opens the c-file with c5." },
    { move_number: 14, player: 'B', move: "dxc5", commentary: "Black accepts the trade to challenge White's pawn structure." },
    { move_number: 15, player: 'W', move: "bxc5", commentary: "White recaptures, launching open lines for the rooks." },
    { move_number: 15, player: 'B', move: "Nxc5", commentary: "Black recaptures with the knight, securing a highly active post." },
    { move_number: 16, player: 'W', move: "Nc4", commentary: "White developed the knight, pointing active pressure at d6." },
    { move_number: 16, player: 'B', move: "b6", commentary: "Black solidifies the c5 knight with ...b6." },
    { move_number: 17, player: 'W', move: "Be3", commentary: "White develops the bishop, targeting the c5 knight." },
    { move_number: 17, player: 'B', move: "Bd7", commentary: "Black connects the queenside pieces actively with ...Bd7. We are now set up to witness the puzzle!" }
  ],
  "exercise_4": [
    { move_number: 1, player: 'W', move: "d4", commentary: "White begins by taking central space." },
    { move_number: 1, player: 'B', move: "Nf6", commentary: "Black responds securely with the knight." },
    { move_number: 2, player: 'W', move: "c4", commentary: "White claims queenside space." },
    { move_number: 2, player: 'B', move: "g6", commentary: "Black moves to fianchetto the bishop." },
    { move_number: 3, player: 'W', move: "Nc3", commentary: "Developing the queen's knight." },
    { move_number: 3, player: 'B', move: "Bg7", commentary: "Black places the bishop on the active diagonal." },
    { move_number: 4, player: 'W', move: "e4", commentary: "White seizes the center with a strong pawn duo." },
    { move_number: 4, player: 'B', move: "d6", commentary: "Black checks White's center from a stable post." },
    { move_number: 5, player: 'W', move: "Nf3", commentary: "White develops the knight, reinforcing d4." },
    { move_number: 5, player: 'B', move: "O-O", commentary: "Black castles safely." },
    { move_number: 6, player: 'W', move: "Be2", commentary: "White plays Be2 solidly." },
    { move_number: 6, player: 'B', move: "e5", commentary: "Black strikes at the d4 centerpiece." },
    { move_number: 7, player: 'W', move: "O-O", commentary: "White castles." },
    { move_number: 7, player: 'B', move: "Nc6", commentary: "Black places maximum pressure on d4." },
    { move_number: 8, player: 'W', move: "d5", commentary: "White locks the center." },
    { move_number: 8, player: 'B', move: "Ne7", commentary: "The black knight retreats, preparing for kingside action." },
    { move_number: 9, player: 'W', move: "Nd2", commentary: "White plays Nd2, clearing path for queenside actions." },
    { move_number: 9, player: 'B', move: "c5", commentary: "Black blocks immediate queenside thrusts with ...c5." },
    { move_number: 10, player: 'W', move: "a3", commentary: "White prepares queenside expansion." },
    { move_number: 10, player: 'B', move: "Ne8", commentary: "Black recycles the knight, paving way for ...f5." },
    { move_number: 11, player: 'W', move: "b4", commentary: "White begins the queenside charge with b4." },
    { move_number: 11, player: 'B', move: "b6", commentary: "Black reinforces the queenside structure." },
    { move_number: 12, player: 'W', move: "Rb1", commentary: "White places the rook on the openable b-file." },
    { move_number: 12, player: 'B', move: "f5", commentary: "Black strikes on the kingside with ...f5!" },
    { move_number: 13, player: 'W', move: "f3", commentary: "White secures e4 defensively." },
    { move_number: 13, player: 'B', move: "f4", commentary: "Black pushes further to lock the kingside, eyeing a storm." },
    { move_number: 14, player: 'W', move: "a4", commentary: "White drives a-pawn to dismantle Black's queenside cover." },
    { move_number: 14, player: 'B', move: "g5", commentary: "Black launches the pawn storm on the kingside." },
    { move_number: 15, player: 'W', move: "a5", commentary: "White continues the dismantling with a5." },
    { move_number: 15, player: 'B', move: "Rf6", commentary: "Black develops the rook via f6 to participate in defense or attack." },
    { move_number: 16, player: 'W', move: "axb6", commentary: "White opens the a-file." },
    { move_number: 16, player: 'B', move: "axb6", commentary: "Black recaptures cleanly." },
    { move_number: 17, player: 'W', move: "Rb1", commentary: "White repositions the rook. We are ready for the tactical test!" }
  ],
  "exercise_5": [
    { move_number: 1, player: 'W', move: "d4", commentary: "White opens with the queen's pawn." },
    { move_number: 1, player: 'B', move: "Nf6", commentary: "Black prevents e4 with ...Nf6." },
    { move_number: 2, player: 'W', move: "c4", commentary: "White secures space with c4." },
    { move_number: 2, player: 'B', move: "g6", commentary: "Black prepares to fianchetto." },
    { move_number: 3, player: 'W', move: "Nc3", commentary: "White develops the queen's knight." },
    { move_number: 3, player: 'B', move: "Bg7", commentary: "Black's bishop mounts the diagonal." },
    { move_number: 4, player: 'W', move: "e4", commentary: "White seizes the center." },
    { move_number: 4, player: 'B', move: "d6", commentary: "Black stops e5 and keeps safe." },
    { move_number: 5, player: 'W', move: "f3", commentary: "Sämisch Variation setup! Solidifying e4." },
    { move_number: 5, player: 'B', move: "O-O", commentary: "Black castles safely." },
    { move_number: 6, player: 'W', move: "Be3", commentary: "White develops the dark-squared bishop." },
    { move_number: 6, player: 'B', move: "e5", commentary: "Black strikes the center centerpiece." },
    { move_number: 7, player: 'W', move: "Nge2", commentary: "White develops the knight to e2 solidly." },
    { move_number: 7, player: 'B', move: "c5", commentary: "Black seeks an active counter by pushing ...c5." },
    { move_number: 8, player: 'W', move: "d5", commentary: "White closes the center, locking spatial advantages." },
    { move_number: 8, player: 'B', move: "e6", commentary: "Black challenges the closed d5 wedge immediately." },
    { move_number: 9, player: 'W', move: "Qd2", commentary: "White sets up the battery." },
    { move_number: 9, player: 'B', move: "exd5", commentary: "Black trades central pawns to open lines." },
    { move_number: 10, player: 'W', move: "cxd5", commentary: "White recaptures cleanly." },
    { move_number: 10, player: 'B', move: "a6", commentary: "Black claims queenside room." },
    { move_number: 11, player: 'W', move: "a4", commentary: "White pushes a4 to halt Black's queenside expansions." },
    { move_number: 11, player: 'B', move: "h6", commentary: "Black plays ...h6, setting up a clever tactical field!" }
  ],
  "exercise_6": [
    { move_number: 1, player: 'W', move: "d4", commentary: "White begins by taking central space." },
    { move_number: 1, player: 'B', move: "Nf6", commentary: "Black develops securely." },
    { move_number: 2, player: 'W', move: "c4", commentary: "White claims queenside space." },
    { move_number: 2, player: 'B', move: "g6", commentary: "Black moves to fianchetto the bishop." },
    { move_number: 3, player: 'W', move: "Nc3", commentary: "Developing the queen's knight." },
    { move_number: 3, player: 'B', move: "Bg7", commentary: "Black places the bishop on the active diagonal." },
    { move_number: 4, player: 'W', move: "e4", commentary: "White seizes the center." },
    { move_number: 4, player: 'B', move: "d6", commentary: "Black checks White's center from a stable post." },
    { move_number: 5, player: 'W', move: "f3", commentary: "Sämisch Variation setup! Solidifying e4." },
    { move_number: 5, player: 'B', move: "O-O", commentary: "Black castles safely." },
    { move_number: 6, player: 'W', move: "Be3", commentary: "White develops the dark-squared bishop." },
    { move_number: 6, player: 'B', move: "e5", commentary: "Black strikes at the center centerpiece." },
    { move_number: 7, player: 'W', move: "Nge2", commentary: "White developments the knight to e2 solidly." },
    { move_number: 7, player: 'B', move: "c5", commentary: "Black counter-strikes with ...c5." },
    { move_number: 8, player: 'W', move: "d5", commentary: "White closes the center, locking space." },
    { move_number: 8, player: 'B', move: "e6", commentary: "Black strikes at the d5 wedge." },
    { move_number: 9, player: 'W', move: "Qd2", commentary: "White establishes the key Qd2 battery." },
    { move_number: 9, player: 'B', move: "exd5", commentary: "Black trades central pawns to open lines." },
    { move_number: 10, player: 'W', move: "cxd5", commentary: "White recaptures." },
    { move_number: 10, player: 'B', move: "a6", commentary: "Black claims queenside space." },
    { move_number: 11, player: 'W', move: "a4", commentary: "White stops queenside moves." },
    { move_number: 11, player: 'B', move: "h6", commentary: "Black plays ...h6, laying a beautiful tactical trap." }
  ],
  "exercise_7": [
    { move_number: 1, player: 'W', move: "d4", commentary: "White claims central authority with the queen's pawn." },
    { move_number: 1, player: 'B', move: "Nf6", commentary: "Black develop the knight hypermodernly." },
    { move_number: 2, player: 'W', move: "c4", commentary: "White increases territory with c4." },
    { move_number: 2, player: 'B', move: "g6", commentary: "Black registers the fianchetto track." },
    { move_number: 3, player: 'W', move: "Nf3", commentary: "White develops the king's knight immediately to f3, eyeing an eventual kingside safety." },
    { move_number: 3, player: 'B', move: "Bg7", commentary: "Black anchors the dark-squared bishop." },
    { move_number: 4, player: 'W', move: "g3", commentary: "The signature of the Fianchetto Variation! White decides to fianchetto their own king's bishop to match Black's." },
    { move_number: 4, player: 'B', move: "O-O", commentary: "Black castles securely." },
    { move_number: 5, player: 'W', move: "Bg2", commentary: "White completes their own fianchetto, creating a solid wall." },
    { move_number: 5, player: 'B', move: "d6", commentary: "Black controls e5 securely." },
    { move_number: 6, player: 'W', move: "O-O", commentary: "White castles into safe terrain." },
    { move_number: 6, player: 'B', move: "Nbd7", commentary: "Black develops the knight to d7, preparing the eventual ...e5 strike." },
    { move_number: 7, player: 'W', move: "Nc3", commentary: "White develops the queen's knight." },
    { move_number: 7, player: 'B', move: "e5", commentary: "Black strikes at the center dynamically!" },
    { move_number: 8, player: 'W', move: "e4", commentary: "White supports d4 by building a solid center with e4." },
    { move_number: 8, player: 'B', move: "c6", commentary: "Black reinforces the center, preparing eventual queen activity." },
    { move_number: 9, player: 'W', move: "h3", commentary: "White plays h3, stopping any ...Ng4 or ...Bg4 jumps by Black's pieces." },
    { move_number: 9, player: 'B', move: "Qb6", commentary: "Black active develops the queen to b6, targeting d4 and b2." },
    { move_number: 10, player: 'W', move: "Re1", commentary: "White spots the queen's position and supports the e4 pawn with the rook." },
    { move_number: 10, player: 'B', move: "exd4", commentary: "Black begins trades in the center to unblock active files." },
    { move_number: 11, player: 'W', move: "Nxd4", commentary: "White recaptures the pawn." },
    { move_number: 11, player: 'B', move: "Re8", commentary: "Black places the rook on the semi-open e-file, exerting pressure on e4." }
  ],
  "exercise_8": [
    { move_number: 1, player: 'W', move: "d4", commentary: "White claims central space by advancing the queen's pawn." },
    { move_number: 1, player: 'B', move: "Nf6", commentary: "Black desarrolls the knight to prevent e4." },
    { move_number: 2, player: 'W', move: "c4", commentary: "White claims queenside space." },
    { move_number: 2, player: 'B', move: "g6", commentary: "Black prepares to fianchetto." },
    { move_number: 3, player: 'W', move: "Nc3", commentary: "White develops the knight." },
    { move_number: 3, player: 'B', move: "Bg7", commentary: "Black places the bishop on the sniper post." },
    { move_number: 4, player: 'W', move: "e4", commentary: "White takes central control with standard pawns." },
    { move_number: 4, player: 'B', move: "d6", commentary: "Black stops e5 and prepares counterplay." },
    { move_number: 5, player: 'W', move: "f4", commentary: "The signature of the Four Pawns Attack! White launches a massive, aggressive pawn storm with f4, hoping to run Black off the board." },
    { move_number: 5, player: 'B', move: "O-O", commentary: "Black castles to safety. In the face of White's overextension, Black trusts their safe king." },
    { move_number: 6, player: 'W', move: "Nf3", commentary: "White develops the knight, reinforcing their giant central wedge." },
    { move_number: 6, player: 'B', move: "c5", commentary: "Black strikes immediately! Undermining White's broad pawn center with the thematic ...c5 choice." },
    { move_number: 7, player: 'W', move: "d5", commentary: "White pushes forward to lock the center, accepting Black's challenge." },
    { move_number: 7, player: 'B', move: "e6", commentary: "Black strikes at the d5 pawn chain dynamically with ...e6." },
    { move_number: 8, player: 'W', move: "Be2", commentary: "White develops the bishop, preparing to castle." },
    { move_number: 8, player: 'B', move: "exd5", commentary: "Black exchanges pawns in the center to create lines." },
    { move_number: 9, player: 'W', move: "cxd5", commentary: "White recaptures cleanly." },
    { move_number: 9, player: 'B', move: "Re8", commentary: "Black positions the rook on the e-file to strike directly at White's loose e4 pawn. The puzzle starts here!" }
  ],
  "exercise_9": [
    { move_number: 1, player: 'W', move: "d4", commentary: "White claims central space by advancing the queen's pawn." },
    { move_number: 1, player: 'B', move: "Nf6", commentary: "Black developing the knight." },
    { move_number: 2, player: 'W', move: "c4", commentary: "White grabs queenside space." },
    { move_number: 2, player: 'B', move: "g6", commentary: "Black prepares the fianchetto." },
    { move_number: 3, player: 'W', move: "Nc3", commentary: "White develops the queen's knight." },
    { move_number: 3, player: 'B', move: "Bg7", commentary: "Black places the bishop on the diagonal." },
    { move_number: 4, player: 'W', move: "e4", commentary: "White grabs the center." },
    { move_number: 4, player: 'B', move: "d6", commentary: "Black stops e5." },
    { move_number: 5, player: 'W', move: "Be2", commentary: "White developments the bishop to e2 solidly." },
    { move_number: 5, player: 'B', move: "O-O", commentary: "Black castles cleanly." },
    { move_number: 6, player: 'W', move: "Bg5", commentary: "The signature of the Averbakh Variation! White pins the f6 knight immediately, making ...e5 more difficult to execute." },
    { move_number: 6, player: 'B', move: "c5", commentary: "Black strikes immediately on the queenside side with ...c5!" },
    { move_number: 7, player: 'W', move: "d5", commentary: "White locks the center." },
    { move_number: 7, player: 'B', move: "e6", commentary: "Black strikes at the center shield with ...e6." },
    { move_number: 8, player: 'W', move: "Qd2", commentary: "White builds the Qd2-Bg5 battery." },
    { move_number: 8, player: 'B', move: "exd5", commentary: "Black trades pawns in the center." },
    { move_number: 9, player: 'W', move: "exd5", commentary: "White recaptures on d5." },
    { move_number: 9, player: 'B', move: "Re8", commentary: "Black places the rook on the e-file." },
    { move_number: 10, player: 'W', move: "Nf3", commentary: "White developed the knight to support." },
    { move_number: 10, player: 'B', move: "Bf5", commentary: "Black activates the dark bishop." },
    { move_number: 11, player: 'W', move: "O-O", commentary: "White castles." },
    { move_number: 11, player: 'B', move: "Nbd7", commentary: "Black develops the knight to d7, preparing pieces." },
    { move_number: 12, player: 'W', move: "Rae1", commentary: "White places the rook on the open e-file. We are set to observe the blow!" }
  ],
  "exercise_10": [
    { move_number: 1, player: 'W', move: "d4", commentary: "White claims central space by advancing the queen's pawn." },
    { move_number: 1, player: 'B', move: "Nf6", commentary: "Black developments the knight." },
    { move_number: 2, player: 'W', move: "c4", commentary: "White grabs queenside space." },
    { move_number: 2, player: 'B', move: "g6", commentary: "Black prepares the fianchetto." },
    { move_number: 3, player: 'W', move: "Nc3", commentary: "White develops the queen's knight." },
    { move_number: 3, player: 'B', move: "Bg7", commentary: "Black places the bishop on the diagonal." },
    { move_number: 4, player: 'W', move: "e4", commentary: "White grabs the center." },
    { move_number: 4, player: 'B', move: "d6", commentary: "Black stops e5." },
    { move_number: 5, player: 'W', move: "h3", commentary: "White plays h3! This prevents ...Ng4/Bg4 jumps, preparing a quiet, prophylactic structure." },
    { move_number: 5, player: 'B', move: "O-O", commentary: "Black castles king to safety." },
    { move_number: 6, player: 'W', move: "Bg5", commentary: "White develops the bishop to g5, pinning the f6 knight." },
    { move_number: 6, player: 'B', move: "Na6", commentary: "Black plays ...Na6! This is a flexible, modern positional move aiming eventually at c5." },
    { move_number: 7, player: 'W', move: "Nf3", commentary: "White develops the knight." },
    { move_number: 7, player: 'B', move: "e5", commentary: "Black strikes at the center centerpiece with e5 anyway." },
    { move_number: 8, player: 'W', move: "d5", commentary: "White locks the center." },
    { move_number: 8, player: 'B', move: "Qe8", commentary: "Black unpins with ...Qe8, preparing to support ...h6/g5." },
    { move_number: 9, player: 'W', move: "Be2", commentary: "White develops the bishop solidly to e2." },
    { move_number: 9, player: 'B', move: "Nh5", commentary: "Black moves the knight to h5, preparing ...Nf4 jumps or kingside expansions." },
    { move_number: 10, player: 'W', move: "Qd2", commentary: "White sets up the battery." },
    { move_number: 10, player: 'B', move: "f5", commentary: "Black launches the thematic ...f5 kingside storm. We are ready!" }
  ],
  "exercise_11": [
    { move_number: 1, player: 'W', move: "d4", commentary: "White occupies the d4 square." },
    { move_number: 1, player: 'B', move: "Nf6", commentary: "Black develops the knight dynamically." },
    { move_number: 2, player: 'W', move: "c4", commentary: "White builds c4 for queenside presence." },
    { move_number: 2, player: 'B', move: "g6", commentary: "Black prepares to fianchetto." },
    { move_number: 3, player: 'W', move: "Nc3", commentary: "White develops the queen's knight." },
    { move_number: 3, player: 'B', move: "Bg7", commentary: "Black's bishop takes its sniper post." },
    { move_number: 4, player: 'W', move: "e4", commentary: "White grabs the center with e4." },
    { move_number: 4, player: 'B', move: "d6", commentary: "Black controls the center from a distance." },
    { move_number: 5, player: 'W', move: "Be3", commentary: "White plays Be3, reinforcing d4. This is a very solid system." },
    { move_number: 5, player: 'B', move: "O-O", commentary: "Black castles to safety." },
    { move_number: 6, player: 'W', move: "Be2", commentary: "White develops the light-squared bishop solidly." },
    { move_number: 6, player: 'B', move: "e5", commentary: "Black counter-strikes with ...e5 immediately." },
    { move_number: 7, player: 'W', move: "d5", commentary: "White locks the center." },
    { move_number: 7, player: 'B', move: "a5", commentary: "Black claims kingside space and secures c5 from immediate white pushes." },
    { move_number: 8, player: 'W', move: "Nf3", commentary: "White develops the knight." },
    { move_number: 8, player: 'B', move: "Na6", commentary: "Black develops the knight to a6, planning to land on c5." },
    { move_number: 9, player: 'W', move: "Nd2", commentary: "White recycles the knight, clearing the f-pawn and prepping queenside action." },
    { move_number: 9, player: 'B', move: "Nd7", commentary: "Black recycles the knight to d7, prepping ...f5 storm." },
    { move_number: 10, player: 'W', move: "O-O", commentary: "White castles into safe terrain. Ready for the critical warning test!" }
  ],
  "game_3": [
    { move_number: 1, player: 'W', move: "d4", commentary: "White claims central space by advancing the queen's pawn." },
    { move_number: 1, player: 'B', move: "Nf6", commentary: "Black develops securely." },
    { move_number: 2, player: 'W', move: "c4", commentary: "White claims queenside space." },
    { move_number: 2, player: 'B', move: "g6", commentary: "Black prepare to fianchetto." },
    { move_number: 3, player: 'W', move: "Nc3", commentary: "White develops the queen's knight." },
    { move_number: 3, player: 'B', move: "Bg7", commentary: "Black's bishop takes its sniper post." },
    { move_number: 4, player: 'W', move: "e4", commentary: "White grabs the center with e4." },
    { move_number: 4, player: 'B', move: "d6", commentary: "Black controls the center from a distance." },
    { move_number: 5, player: 'W', move: "Nf3", commentary: "White developers the knight." },
    { move_number: 5, player: 'B', move: "O-O", commentary: "Black castles securely." },
    { move_number: 6, player: 'W', move: "Be2", commentary: "White plays Be2 solidly." },
    { move_number: 6, player: 'B', move: "e5", commentary: "Black counter-strikes with ...e5 immediately." },
    { move_number: 7, player: 'W', move: "d5", commentary: "White locks the center." },
    { move_number: 7, player: 'B', move: "a5", commentary: "Black claims queenside space." },
    { move_number: 8, player: 'W', move: "Bg5", commentary: "The Petrosian Variation! White pin the f6 knight to disrupt Black's kingside build." },
    { move_number: 8, player: 'B', move: "h6", commentary: "Black immediately questions the bishop with ...h6." },
    { move_number: 9, player: 'W', move: "Bh4", commentary: "White retreats the bishop to maintain the pin." },
    { move_number: 9, player: 'B', move: "Na6", commentary: "Black develops the knight to a6, preparing ...Nc5." },
    { move_number: 10, player: 'W', move: "Nd2", commentary: "White repositions the knight, clear the f-pawn." },
    { move_number: 10, player: 'B', move: "Qe8", commentary: "Black unpins the f6 knight with ...Qe8, allowing dynamic kingside expansions." }
  ],
  "game_28": [
    { move_number: 1, player: 'W', move: "d4", commentary: "White begins with the queen's pawn." },
    { move_number: 1, player: 'B', move: "Nf6", commentary: "Black prevents e4." },
    { move_number: 2, player: 'W', move: "c4", commentary: "White grabs queenside space." },
    { move_number: 2, player: 'B', move: "g6", commentary: "Black prepares the fianchetto." },
    { move_number: 3, player: 'W', move: "Nc3", commentary: "White develops the queen's knight." },
    { move_number: 3, player: 'B', move: "Bg7", commentary: "Black's bishop takes the sniper post." },
    { move_number: 4, player: 'W', move: "e4", commentary: "White grabs the center with e4." },
    { move_number: 4, player: 'B', move: "d6", commentary: "Black controls the center from a distance." },
    { move_number: 5, player: 'W', move: "Nf3", commentary: "White develops the knight." },
    { move_number: 5, player: 'B', move: "O-O", commentary: "Black castles safely." },
    { move_number: 6, player: 'W', move: "Be2", commentary: "White plays Be2 solidly." },
    { move_number: 6, player: 'B', move: "e5", commentary: "Black counter-strikes with ...e5." },
    { move_number: 7, player: 'W', move: "O-O", commentary: "White castles. Entering the Classical Main Line." },
    { move_number: 7, player: 'B', move: "Nc6", commentary: "Black developers the knight, placing pressure on d4." },
    { move_number: 8, player: 'W', move: "d5", commentary: "White locks the center." },
    { move_number: 8, player: 'B', move: "Ne7", commentary: "The black knight retreats, preparing for kingside action." },
    { move_number: 9, player: 'W', move: "Ne1", commentary: "The Classical main approach! White retreats the f3 knight to e1 to free the f2-f3 structures and prepare f2-f4 or g2-g4." },
    { move_number: 9, player: 'B', move: "Nd7", commentary: "Black recycles the knight, freeing the f7-f5 pawn strike." },
    { move_number: 10, player: 'W', move: "Nd3", commentary: "White places the knight on d3 to support the queenside c4-c5 break." },
    { move_number: 10, player: 'B', move: "f5", commentary: "Black begins the kingside pawn expansion with ...f5!" },
    { move_number: 11, player: 'W', move: "Bd2", commentary: "White develops the bishop to d2 solidly, keeping options flexible." },
    { move_number: 11, player: 'B', move: "Nf6", commentary: "Black recycles the knight back to f6 to threaten e4 and support h5." },
    { move_number: 12, player: 'W', move: "f3", commentary: "White reinforces e4 securely." },
    { move_number: 12, player: 'B', move: "f4", commentary: "Black pushes ...f4 to lock the center, starting a full kingside pawn storm." },
    { move_number: 13, player: 'W', move: "c5", commentary: "White breaks on c5 to dismantle Black's queenside shield." },
    { move_number: 13, player: 'B', move: "g5", commentary: "Black pushes ...g5, driving the kingside pawn storm forward!" },
    { move_number: 14, player: 'W', move: "Rc1", commentary: "White places the rook on the semi-open c-file, pointing at c7." },
    { move_number: 14, player: 'B', move: "Ng6", commentary: "Black desarrolla the e7 knight to g6 to jump to h4 or f4 later." },
    { move_number: 15, player: 'W', move: "cxd6", commentary: "White opens the c-file." },
    { move_number: 15, player: 'B', move: "cxd6", commentary: "Black recaptures cleanly to keep structure." },
    { move_number: 16, player: 'W', move: "Nb5", commentary: "White's knight jumps to b5, aiming at the weak c7 square." },
    { move_number: 16, player: 'B', move: "Rf7", commentary: "Black's rook on f7 defends c7 perfectly while staying active." },
    { move_number: 17, player: 'W', move: "Qc2", commentary: "White builds a powerful queen-rook battery on the c-file." },
    { move_number: 17, player: 'B', move: "Ne8", commentary: "Black defends c7 further with ...Ne8." },
    { move_number: 18, player: 'W', move: "a4", commentary: "White gains queenside spatial extensions with a4." },
    { move_number: 18, player: 'B', move: "h5", commentary: "Black steps the pawn to h5, setting up the ultimate kingside breakthrough." },
    { move_number: 19, player: 'W', move: "Nf2", commentary: "White reposition the knight to f2 to assist in kingside defense." },
    { move_number: 19, player: 'B', move: "Bf8", commentary: "Black repositions the dark bishop to f8 to guard d6 and clear the g7 rook." },
    { move_number: 20, player: 'W', move: "a5", commentary: "White pushes a5, looking for queenside invasion spots." },
    { move_number: 20, player: 'B', move: "Bd7", commentary: "Black developments the light bishop to d7, securing files." },
    { move_number: 21, player: 'W', move: "Qb3", commentary: "White repositions the queen." },
    { move_number: 21, player: 'B', move: "Rg7", commentary: "Black aligns the rook behind the g-pawn. The scene is set for a historic clash!" }
  ]
};

// Fallback dynamic generator to handle clean, robust parsed moves if they parsed a custom book page
export function getOpeningMovesForPage(page: any): ChessMove[] {
  if (!page || !page.preparsedJson) return [];
  const gid = page.preparsedJson.game_id;
  if (gid && OPEN_SETUP_MAP[gid]) {
    return OPEN_SETUP_MAP[gid];
  }

  // Generate fallbackMoves list automatically with simple educational boilerplate for any other custom game page!
  const initialMovesStr = page.preparsedJson.initial_moves || '';
  if (!initialMovesStr) return [];

  const moves = initialMovesStr
    .replace(/\d+\.+/g, '')
    .replace(/\s+/g, ' ')
    .trim()
    .split(' ')
    .filter(token => !/^\d+$/.test(token));

  const result: ChessMove[] = [];
  let moveNum = 1;
  let player: 'W' | 'B' = 'W';

  for (let i = 0; i < moves.length; i++) {
    const rawMove = moves[i];
    if (!rawMove) continue;

    let commentary = "";
    if (rawMove === "d4") {
      commentary = "White starts with Queen's pawn opening. Fighting for spatial control of central e5/c5 complexes.";
    } else if (rawMove === "Nf6") {
      commentary = "Black develops the knight to f6, blocking an immediate e4 advance and choosing dynamic piece defense.";
    } else if (rawMove === "c4") {
      commentary = "White claims queenside space, preparing behind development Nc3 and putting pressure on d5.";
    } else if (rawMove === "g6") {
      commentary = "The standard King's Indian defense preparation! Black prepares the bishop for kingside fianchetto.";
    } else if (rawMove === "Nc3") {
      commentary = "White develops the knight to c3 to put eyes on e4 and d5 center squares.";
    } else if (rawMove === "Bg7") {
      commentary = "Black places the bishop on the safe castle fianchetto line g7. It operates as a long-range defender.";
    } else if (rawMove === "e4") {
      commentary = "White takes control of the full center with pawns on c4-d4-e4.";
    } else if (rawMove === "d6") {
      commentary = "Black controls e5 to prevent White's central push, keeping dynamic strike-back options flexible.";
    } else {
      commentary = `Played ${rawMove}. A classic setup move continuing the opening progression to establish center coordination.`;
    }

    result.push({
      move_number: moveNum,
      player,
      move: rawMove,
      commentary
    });

    if (player === 'B') {
      moveNum++;
      player = 'W';
    } else {
      player = 'B';
    }
  }

  return result;
}
