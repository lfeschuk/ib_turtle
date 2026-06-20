import { SampleBookPage, ParsedChessGame, ChessMove } from './types';

export interface CompactIllustrativeGame {
  num: number;
  white: string;
  black: string;
  event: string;
  year: number;
  chapter: number;
  chapterTitle: string;
  page: number;
  initial: string;
  moves: Array<{ m: string; c: string }>; // Move symbol (SAN) and commentary
}

export const COMPACT_68_GAMES: CompactIllustrativeGame[] = [
  {
    num: 1,
    white: "Salgado",
    black: "Gallagher",
    event: "L'Hospitalet",
    year: 1992,
    chapter: 1,
    chapterTitle: "Alternatives to 7 O-O",
    page: 14,
    initial: "d4 Nf6 c4 g6 Nc3 Bg7 e4 d6 Nf3 O-O Be2 e5 dxe5 dxe5 Qxd8 Rxd8 Bg5 Re8 10 Nd5 Nxd5 11 cxd5 c6 12 Bc4 cxd5 13 Bxd5 Nd7",
    moves: [
      { m: "Nd2", c: "White shifts the knight on f3 to d2 to prepare for possible center maneuvers and allow the f-pawn to react if necessary." },
      { m: "Nc5", c: "Black develops the knight to the active c5 square, placing pressure on e4 and preparing to anchor active queenside play." },
      { m: "Nc4?!", c: "A slight mistake as it allows Black some tricks based on ...Nxe4, while the knight may also get booted by ...b7-b5 at some point. Best is 15. O-O! and after 15...Ne6 leading to equality." },
      { m: "Bf8", c: "This keeps the knight out of d6 and also transfers the bishop to a more active post. There is not much life on the long diagonal." },
      { m: "O-O", c: "On the last move *castling was correct* (15. O-O! was best). Doing so now is rather risky as Black is already fully mobilized to launch a counterstrike." },
      { m: "Be6", c: "Developing the light-squared bishop with tempo, attacking White's central light-square outpost on d5." },
      { m: "Bxe6", c: "White trades bishop for bishop. This relieves tension but also weakens White's light squares slightly." },
      { m: "Rxe6!", c: "Recapturing with the rook is very active, preparing to slide the rook over to command open ranks." },
      { m: "f3", c: "White reinforces the e4-pawn, which was under a threat, preparing to solidify the kingside setup." },
      { m: "b5", c: "Black immediately pushes on the queenside, gaining space and asking immediate questions of White's c4 knight." },
      { m: "Ne3", c: "White retreats the knight to a defensive outpost on e3, attempting to anchor the center." },
      { m: "Rd6", c: "Black moves the rook to d6, preparing to double rooks along the d-file to claim total vertical dominance." },
      { m: "Rfd1", c: "White challenges Black's control of the d-file by shifting the f-rook to d1." },
      { m: "Rad8", c: "Black doubles rooks on the d-file, completing the strategic setup and grabbing control." },
      { m: "Rxd6", c: "Trading one pair of rooks to ease the horizontal pressure." },
      { m: "Rxd6", c: "Black recaptures on d6, maintaining the absolute file control on the d-file." },
      { m: "Rd1", c: "White attempts to trade the remaining rooks, as Black's piece placement remains highly coordinated." },
      { m: "Rxd1+", c: "Black swaps the rooks, shifting the battle fully into a knight endgame where Black's pieces are more active." },
      { m: "Nxd1", c: "White recaptures with the knight, leaving both kings to mobilize." },
      { m: "Ne6", c: "Kicking off the central knight maneuver to control the critical squares." },
      { m: "Ne3", c: "White repositions the knight on e3, contesting key entry points." },
      { m: "Nd4", c: "Black plants a powerful knight on d4, centralized and dominating white territory." },
      { m: "Kf1", c: "The white king begins to walk up to assist in defense." },
      { m: "Bc5", c: "Activating the bishop to point at the weak f2 pawn. Black maintains a comfortable positional advantage in this endgame." }
    ]
  },
  {
    num: 2,
    white: "Acebal",
    black: "Gallagher",
    event: "Candas",
    year: 1992,
    chapter: 1,
    chapterTitle: "Alternatives to 7 O-O",
    page: 15,
    initial: "d4 Nf6 c4 g6 Nc3 Bg7 e4 d6 Nf3 O-O Be2 e5 dxe5 dxe5 Qxd8 Rxd8 Bg5 Re8 10 Nd5 Nxd5 11 cxd5 c6 12 Bc4 cxd5 13 Bxd5 Nd7 14 Nd2 Nc5 15 Nc4 Bf8 16 O-O Be6 17 Bxe6 Rxe6!",
    moves: [
      { m: "f3", c: "Shoring up the central e4 pawn. Black's rooks are highly active and will soon seize the queenside files." },
      { m: "b5", c: "Kicking the knight on c4. Decreases white territory control and stakes space on the queenside." },
      { m: "Ne3", c: "White retreats the knight to a defensive outpost on e3, attempting to anchor the center." },
      { m: "h6", c: "Black immediately asks questions of the white bishop on g5, aiming to gain space on the kingside." },
      { m: "Bh4", c: "The bishop retreats to h4, keeping the diagonal pressure but remaining slightly passive." },
      { m: "Nd3", c: "Active jump! The knight takes up a commanding outpost on d3, eyeing soft squares in White’s camp." }
    ]
  },
  {
    num: 3,
    white: "Lyrberg",
    black: "Bologan",
    event: "Oslo",
    year: 1994,
    chapter: 1,
    chapterTitle: "Alternatives to 7 O-O",
    page: 18,
    initial: "d4 Nf6 c4 g6 Nc3 Bg7 e4 d6 Nf3 O-O Be2 e5 d5 a5 Bg5 h6 Bh4 Na6 Nd2 Qe8 Bg3 Nh5",
    moves: [
      { m: "h4", c: "A sharp, aggressive thrust! White commits to locking Black's options on the kingside." },
      { m: "Nxg3", c: "Black immediately jumps on the opportunity, trading the knight for the active bishop." },
      { m: "fxg3", c: "Recaptured. The open f-pawn gives White a solid center but opens up counter-opportunities for Black." },
      { m: "g5", c: "Aggressive pawn charge! Black stakes direct claims, seeking space on the kingside to launch a counter-attack." },
      { m: "Nh2", c: "White retreats the knight defensively, preparing to absorb the upcoming pawn storm." }
    ]
  },
  {
    num: 4,
    white: "Mariano",
    black: "Cvitan",
    event: "Mendrisio",
    year: 1999,
    chapter: 1,
    chapterTitle: "Alternatives to 7 O-O",
    page: 21,
    initial: "d4 Nf6 c4 g6 Nc3 Bg7 e4 d6 Nf3 O-O Be2 e5 d5 Na6 Bg5 h6 Bh4",
    moves: [
      { m: "Qe8", c: "The queen steps out of the pin of the dark-squared bishop, preparing a future f5 pawn thrust." },
      { m: "Nd2", c: "White maneuvers the knight towards a standard queenside blockading square." },
      { m: "Nh7", c: "Preparing the thematic f7-f5 push to challenge White's central space advantage." },
      { m: "O-O", c: "White castles safely. Black now has the green light to initiate King's Indian kingside action." }
    ]
  },
  {
    num: 5,
    white: "Shulman",
    black: "Bakhtadze",
    event: "Holon",
    year: 1995,
    chapter: 1,
    chapterTitle: "Alternatives to 7 O-O",
    page: 23,
    initial: "d4 Nf6 c4 g6 Nc3 Bg7 e4 d6 Nf3 O-O Be2 e5 d5 Nbd7 Bg5 h6 Bh4 a6 Nd2 Qe8",
    moves: [
      { m: "O-O", c: "White completes castling. Both sides are fully mobilized and ready for positional warfare." },
      { m: "Nh7", c: "Moving the defensive knight out of the way to prepare the thematic f7-f5 pawn storm." },
      { m: "a3", c: "White prepares queenside expansion with b2-b4, seeking space to open lines." },
      { m: "f5", c: "Black lashes out in the center and kingside, initiating standard tactical counterplay." }
    ]
  },
  {
    num: 6,
    white: "I. Sokolov",
    black: "Shirov",
    event: "FIDE World Ch, Las Vegas",
    year: 1999,
    chapter: 1,
    chapterTitle: "Alternatives to 7 O-O",
    page: 25,
    initial: "d4 Nf6 c4 g6 Nc3 Bg7 e4 d6 Nf3 O-O Be2 e5 d5 Na6 O-O Nc5 Qc2 a5 Bg5 h6 Be3 b6 Nd2",
    moves: [
      { m: "Ng4", c: "An active challenge! Shirov immediately jumps to swap White's active dark-squared bishop." },
      { m: "Bxg4", c: "White accepts the swap. Trading bishop for knight to maintain spatial control." },
      { m: "Bxg4", c: "Recaptured. Black gains the bishop pair and an extremely healthy dynamic game." },
      { m: "b3", c: "A solid defensive structure, supporting the c4 pawn and preparing for black's dynamic expansion." }
    ]
  },
  {
    num: 7,
    white: "Tukmakov",
    black: "Gallagher",
    event: "Basel",
    year: 1999,
    chapter: 2,
    chapterTitle: "7 O-O: Alternatives to 7...Nc6",
    page: 31,
    initial: "d4 Nf6 c4 g6 Nc3 Bg7 e4 d6 Nf3 O-O Be2 e5 O-O exd4 Nxd4 Re8 f3 c6 Kh1",
    moves: [
      { m: "Nbd7", c: "Black develops the knight towards b6 to control c4 and e4, bypassing the standard d7 square." },
      { m: "Nc2", c: "White centralizes the knight to d4 or d3, keeping an eye on the d6 pawn." },
      { m: "Nb6", c: "The knight lands on b6, targeting c4 and putting pressure on White's queenside layout." },
      { m: "b3", c: "Shoring up the c4 pawn, but slightly weakening the long a1-h8 dark diagonal." }
    ]
  },
  {
    num: 8,
    white: "Portisch",
    black: "Cramling",
    event: "Marbella",
    year: 1999,
    chapter: 2,
    chapterTitle: "7 O-O: Alternatives to 7...Nc6",
    page: 32,
    initial: "d4 Nf6 c4 g6 Nc3 Bg7 e4 d6 Nf3 O-O Be2 e5 O-O Nc6 Be3 Re8 d5 Nd4 Nxd4 exd4 Bxd4 Nxe4 Bxg7 Kxg7 Nxe4 Rxe4",
    moves: [
      { m: "Bd3", c: "Developing the bishop to attack the active black rook on e4." },
      { m: "Re8", c: "The rook retreats to safety, maintaining control of the open e-file." },
      { m: "Qd2", c: "The white queen connects the rooks and prepares for active central deployment." },
      { m: "Qf6", c: "The black queen takes an active post, neutralizing White's major piece development." }
    ]
  },
  {
    num: 9,
    white: "Biriukov",
    black: "Svidler",
    event: "St Petersburg",
    year: 1997,
    chapter: 2,
    chapterTitle: "7 O-O: Alternatives to 7...Nc6",
    page: 35,
    initial: "d4 Nf6 c4 g6 Nc3 Bg7 e4 d6 Nf3 O-O Be2 e5 O-O exd4 Nxd4 Re8 f3 c6 Kh1 d5 cxd5 cxd5 Bg5",
    moves: [
      { m: "dxe4", c: "Svidler accepts the central challenge, opening file lines for the heavy pieces." },
      { m: "Nxe4", c: "White recaptures, trying to maintain spatial pressure." },
      { m: "Nbd7", c: "Black brings the knight out to support the solid center and challenge White's active units." },
      { m: "Nxf6+", c: "White forcedly trades on f6, liquidating the knight tension." }
    ]
  },
  {
    num: 10,
    white: "Pelletier",
    black: "Gallagher",
    event: "Neuchatel",
    year: 2001,
    chapter: 2,
    chapterTitle: "7 O-O: Alternatives to 7...Nc6",
    page: 36,
    initial: "d4 Nf6 c4 g6 Nc3 Bg7 e4 d6 Nf3 O-O Be2 e5 O-O Na6 Re1 c6 Bf1 Bg4 d5 Bxf3 Qxf3 cxd5 cxd5 Nc5",
    moves: [
      { m: "b4", c: "An active thrust on the queenside, aiming to kick the well-placed black knight from c5." },
      { m: "Ncd7", c: "The knight retreats, but Black's dark-square bishop has a wide-open path." },
      { m: "a4", c: "Pushing queenside pawns to restrict Black's counterplay." },
      { m: "Rc8", c: "Seizing the open c-file instantly, finding counterplay on the queenside." }
    ]
  },
  {
    num: 11,
    white: "Piket",
    black: "Nedev",
    event: "European Ch, Ohrid",
    year: 2001,
    chapter: 2,
    chapterTitle: "7 O-O: Alternatives to 7...Nc6",
    page: 39,
    initial: "d4 Nf6 c4 g6 Nc3 Bg7 e4 d6 Nf3 O-O Be2 e5 O-O Na6 Bg5 h6 Be3 Ng4 Bc1 c6 d5 f5 h3 Nf6",
    moves: [
      { m: "exf5", c: "White voluntarily releases center tension to expose Black's castled king shelter." },
      { m: "gxf5", c: "Black recaptures toward the center, accepting an isolated f-pawn for open attacking files." },
      { m: "Nh4", c: "White eyeing the weak f5-pawn and key light squares." },
      { m: "e6", c: "Black strikes back in the center to challenge White's d5-pawn." },
      { m: "dxe6", c: "Trading central control. Piket attacks the d-file." },
      { m: "Bxe6", c: "Black recaptures with the bishop, activating all minor units beautifully." }
    ]
  },
  {
    num: 12,
    white: "Roeder",
    black: "Hebden",
    event: "Bern",
    year: 1992,
    chapter: 3,
    chapterTitle: "7 O-O Nc6: Main Line with 9 Ne1",
    page: 45,
    initial: "d4 Nf6 c4 g6 Nc3 Bg7 e4 d6 Nf3 O-O Be2 e5 O-O Nc6 d5 Ne7 Ne1 Nd7 Nd3 f5 f3 f4 Bd2 g5 b4 Nf6",
    moves: [
      { m: "c5", c: "White attacks on the queenside. Standard practice: White plays on the queenside, Black on the kingside!" },
      { m: "Ng6", c: "Centralizing the knight, preparing to launch a direct pawn storm on the King." },
      { m: "a4", c: "Advancing the a-pawn. White launches their storm, aiming to open files on the left." },
      { m: "h5", c: "The counter-storm begins! Black pushes h5, aiming for g5-g4 to crack White's shelter." }
    ]
  },
  {
    num: 13,
    white: "Rogers",
    black: "Sznapik",
    event: "Thessaloniki Olympiad",
    year: 1988,
    chapter: 3,
    chapterTitle: "7 O-O Nc6: Main Line with 9 Ne1",
    page: 47,
    initial: "d4 Nf6 c4 g6 Nc3 Bg7 e4 d6 Nf3 O-O Be2 e5 O-O Nc6 d5 Ne7 Ne1 Nd7 Nd3 f5 exf5 Nxf5 f3 Nf6 Nf2 Nd4 Nfe4",
    moves: [
      { m: "Bf5", c: "An active development, placing pressure on White's centralized knight outpost." },
      { m: "Nxf6+", c: "White trades knights to liquidise center density." },
      { m: "Qxf6", c: "Black recaptures with the queen, eyeing active kingside diagonals." },
      { m: "Be3", c: "White develops their dark-squared bishop, solidifying their center camp." }
    ]
  },
  {
    num: 14,
    white: "Gyimesi",
    black: "Cvitan",
    event: "Chiasso",
    year: 1994,
    chapter: 3,
    chapterTitle: "7 O-O Nc6: Main Line with 9 Ne1",
    page: 49,
    initial: "d4 Nf6 c4 g6 Nc3 Bg7 e4 d6 Nf3 O-O Be2 e5 O-O Nc6 d5 Ne7 Ne1 Nd7 Nd3 f5 Bd2 Nf6 f3 f4 c5 g5 Rc1 Ng6 cxd6 cxd6",
    moves: [
      { m: "Nb5", c: "An aggressive jump, targeting the weak c7 square in Black's camp." },
      { m: "Rf7", c: "Superb defense! Black shifts the rook to defend c7 and prepare for kingside expansion." },
      { m: "a4", c: "White continues their queenside charge, gaining vital space." },
      { m: "g4", c: "Black replies by immediately pushing on the kingside to begin a royal mating storm." }
    ]
  },
  {
    num: 15,
    white: "Pinter",
    black: "Nunn",
    event: "Thessaloniki Olympiad",
    year: 1988,
    chapter: 3,
    chapterTitle: "7 O-O Nc6: Main Line with 9 Ne1",
    page: 51,
    initial: "d4 Nf6 c4 g6 Nc3 Bg7 e4 d6 Nf3 O-O Be2 e5 O-O Nc6 d5 Ne7 Ne1 Nd7 Nd3 f5 Bd2 Nf6 f3 f4 c5 g5 Rc1 Ng6 Be1 Rf7",
    moves: [
      { m: "cxd6", c: "White takes on d6, seeking to crack open the c-file for their active rooks." },
      { m: "cxd6", c: "Black recaptures, maintaining solid central control." },
      { m: "Nb5", c: "White leaps targeting d6 and c7, trying to distract Black from the kingside attack." },
      { m: "Ne8", c: "John Nunn defends calmly, routing the knight back to defend the weak c7 coordinates." }
    ]
  },
  {
    num: 16,
    white: "Korchnoi",
    black: "Xie Jun",
    event: "Wentzou",
    year: 1995,
    chapter: 3,
    chapterTitle: "7 O-O Nc6: Main Line with 9 Ne1",
    page: 53,
    initial: "d4 Nf6 c4 g6 Nc3 Bg7 e4 d6 Nf3 O-O Be2 e5 O-O Nc6 d5 Ne7 Ne1 Nd7 Nd3 f5 Bd2 Nf6 f3 f4 c5 g5 Qb3 Kh8 Rfc1 Ng6",
    moves: [
      { m: "cxd6", c: "Korchnoi initiates the file-opening sequence, aiming to leverage his rook pressure on c1." },
      { m: "cxd6", c: "Recaptured safely. The center remains closed, but the c-file is ready for battle." },
      { m: "Nb5", c: "White lands on the key b5 outpost, threatening the c7 pawn." },
      { m: "Ne8", c: "A crucial defense: the knight steps back to guard c7 and cover positional weaknesses." }
    ]
  },
  {
    num: 17,
    white: "Koutsin",
    black: "Frolov",
    event: "Kiev",
    year: 1995,
    chapter: 3,
    chapterTitle: "7 O-O Nc6: Main Line with 9 Ne1",
    page: 55,
    initial: "d4 Nf6 c4 g6 Nc3 Bg7 e4 d6 Nf3 O-O Be2 e5 O-O Nc6 d5 Ne7 Ne1 Nd7 f4 f5 Nd3 fxe4 Nxe4 Nf5",
    moves: [
      { m: "fxe5", c: "White trades in the center, trying to clear files for the active heavy pieces." },
      { m: "Nxe5", c: "Black centralizes the knight beautifully on e5." },
      { m: "Nxe5", c: "White trades back. Keeping piece activity equal." },
      { m: "Bxe5", c: "Black's bishop recaptures on e5, becoming an extremely strong and active piece on the main diagonal." }
    ]
  },
  {
    num: 18,
    white: "Borges Mateos",
    black: "Pecorelli",
    event: "Cali",
    year: 2000,
    chapter: 3,
    chapterTitle: "7 O-O Nc6: Main Line with 9 Ne1",
    page: 57,
    initial: "d4 Nf6 c4 g6 Nc3 Bg7 e4 d6 Nf3 O-O Be2 e5 O-O Nc6 d5 Ne7 Ne1 Nd7 f4 f5 Nd3 fxe4 Nxe4 Nf5 Bg4",
    moves: [
      { m: "exf4", c: "Black takes the central pawn, shattering White's pawn structure." },
      { m: "Bxf4", c: "White recaptures with the bishop, activating their minor forces." },
      { m: "Nf6", c: "Black centralizes the knight to challenge White's active e4 piece." },
      { m: "Nxf6+", c: "White initiates the knight trade to clear center space." }
    ]
  },
  {
    num: 19,
    white: "Opalic",
    black: "Socko",
    event: "Passau",
    year: 1999,
    chapter: 3,
    chapterTitle: "7 O-O Nc6: Main Line with 9 Ne1",
    page: 58,
    initial: "d4 Nf6 c4 g6 Nc3 Bg7 e4 d6 Nf3 O-O Be2 e5 O-O Nc6 d5 Ne7 Ne1 Nd7 Nd3 f5 Bd2 Nf6 f3 f4 Be1 g5",
    moves: [
      { m: "Bf2", c: "Developing the bishop to e1-f2, aiming to support the queenside b4-c5 push." },
      { m: "h5", c: "Socko lashes out with ...h5, fueling the imminent kingside mating attack." },
      { m: "c5", c: "White locks the queenside or tries to block Black's options." },
      { m: "g4", c: "Black continues the visual pawn storm, preparing the lines of fire." }
    ]
  },
  {
    num: 20,
    white: "Van Wely",
    black: "Fedorov",
    event: "European Team Ch, Batumi",
    year: 1999,
    chapter: 4,
    chapterTitle: "7 O-O Nc6: Alternatives to 9 Ne1",
    page: 62,
    initial: "d4 Nf6 c4 g6 Nc3 Bg7 e4 d6 Nf3 O-O Be2 e5 O-O Nc6 d5 Ne7 Nd2 a5 a3 Nd7 Rb1 f5 b4 Kh8 f3 Ng8",
    moves: [
      { m: "c5", c: "White strikes at the queenside, aiming to open the b-file and c-file for major piece assets." },
      { m: "dxc5", c: "Black exchanges pawns in the center to maintain structural integrity." },
      { m: "Nc4", c: "White's knight recaptures, gaining an exceptionally active post." },
      { m: "Ngf6", c: "Black's defensive knight shifts back, protecting the vulnerable e4 / d5 grid." }
    ]
  },
  {
    num: 21,
    white: "Kamsky",
    black: "Kasparov",
    event: "New York Intel rapid",
    year: 1994,
    chapter: 4,
    chapterTitle: "7 O-O Nc6: Alternatives to 9 Ne1",
    page: 64,
    initial: "d4 Nf6 c4 g6 Nc3 Bg7 e4 d6 Nf3 O-O Be2 e5 O-O Nc6 d5 Ne7 Nd2 c5 a3 Ne8 b4 b6 Rb1 f5 f3 f4 a4 g5 a5",
    moves: [
      { m: "Rf6", c: "The legendary Kasparov rook lift! Preparing ...Rh6 to attack White's king." },
      { m: "axb6", c: "Kamsky exchanges pawns to open up the a-file for rook intrusion." },
      { m: "axb6", c: "Kasparov recaptures, keeping the solid queenside structure intact." },
      { m: "Rb3", c: "White lifts the rook to b3, preparing to double heavy pieces on the b-file." }
    ]
  },
  {
    num: 22,
    white: "Kobalija",
    black: "Smirnov",
    event: "Russian Ch, Elista",
    year: 2001,
    chapter: 4,
    chapterTitle: "7 O-O Nc6: Alternatives to 9 Ne1",
    page: 68,
    initial: "d4 Nf6 c4 g6 Nc3 Bg7 e4 d6 Nf3 O-O Be2 e5 O-O Nc6 d5 Ne7 Nd2 Nd7 b4 f5 a4 Nf6 Ba3 b6",
    moves: [
      { m: "exf5", c: "White exchanges on f5, seeking to limit Black's kingside mating network." },
      { m: "gxf5", c: "Recaptures active. Black maintains a strong footprint in the center." },
      { m: "c5", c: "White tries to block Black's queenside structure and occupy d6." },
      { m: "bxc5", c: "Trading pawns on c5, opening files for direct tactical play." }
    ]
  },
  {
    num: 23,
    white: "Babula",
    black: "Degraeve",
    event: "Istanbul Olympiad",
    year: 2000,
    chapter: 4,
    chapterTitle: "7 O-O Nc6: Alternatives to 9 Ne1",
    page: 68,
    initial: "d4 Nf6 c4 g6 Nc3 Bg7 e4 d6 Nf3 O-O Be2 e5 O-O Nc6 d5 Ne7 Nd2 Nd7 b4 f5 a4 Nf6 f3 f4 c5 g5 Nc4 Ng6",
    moves: [
      { m: "Ba3", c: "Deploying the bishop to a3, adding pressure to the d6 pawn." },
      { m: "Rf7", c: "The classic KID rook lift, providing double-faced protection on f7 and c7." },
      { m: "b5", c: "White charges forward with b4-b5, opening queenside files." },
      { m: "Bf8", c: "Degraeve defends calmly, anchoring the c5, d6 system." }
    ]
  },
  {
    num: 24,
    white: "Xu Jun",
    black: "Ye Jiangchuan",
    event: "Shanghai",
    year: 2001,
    chapter: 4,
    chapterTitle: "7 O-O Nc6: Alternatives to 9 Ne1",
    page: 69,
    initial: "d4 Nf6 c4 g6 Nc3 Bg7 e4 d6 Nf3 O-O Be2 e5 O-O Nc6 d5 Ne7 Nd2 Nd7 b4 f5 a4 Nf6 f3 f4 Ba3 g5 c5 Ng6 b5",
    moves: [
      { m: "b6", c: "Black blocks the queenside, aiming to neutralize White's immediate storm." },
      { m: "Nc4", c: "White redirects the knight to maintain maximum central tension." },
      { m: "Ne8", c: "Solidifying the vulnerable d6 square, ready to start the h7-h5 kingside rush." }
    ]
  },
  {
    num: 25,
    white: "Quinn",
    black: "Shirov",
    event: "European Team Ch, Leon",
    year: 2001,
    chapter: 4,
    chapterTitle: "7 O-O Nc6: Alternatives to 9 Ne1",
    page: 70,
    initial: "d4 Nf6 c4 g6 Nc3 Bg7 e4 d6 Nf3 O-O Be2 e5 O-O Nc6 d5 Ne7 Nd2 Nd7 b4 f5 f3 f4 c5 g5 Nc4 Nf6",
    moves: [
      { m: "Ba3", c: "White aligns a diagonal laser battery on d6." },
      { m: "Ng6", c: "Shirov ignores queenside noise and groups his units for a checkmate assault." },
      { m: "b5", c: "White races forward. Speed is absolutely of the essence in these double-edged battles." },
      { m: "h5", c: "Black's kingside storm gets the green light!" }
    ]
  },
  {
    num: 26,
    white: "Beliavsky",
    black: "Solak",
    event: "Europe Ch, Saint Vincent",
    year: 2000,
    chapter: 4,
    chapterTitle: "7 O-O Nc6: Alternatives to 9 Ne1",
    page: 73,
    initial: "d4 Nf6 c4 g6 Nc3 Bg7 e4 d6 Nf3 O-O Be2 e5 O-O Nc6 d5 Ne7 Nd2 Nd7 b4 f5 Nb3 Nf6 f3 f4",
    moves: [
      { m: "c5", c: "Establishing a strong queenside pawn presence, targeting the d6 wedge." },
      { m: "g5", c: "Solak starts the kingside crusade with g5, preparing the g4-f3 breakthroughs." },
      { m: "Bd2", c: "Developing the dark-squared bishop to d2 to connect rooks." },
      { m: "Ng6", c: "The knight joins the kingside attack, aiming for f4 or h4." }
    ]
  },
  {
    num: 27,
    white: "Nemet",
    black: "Gallagher",
    event: "Zurich",
    year: 1995,
    chapter: 4,
    chapterTitle: "7 O-O Nc6: Alternatives to 9 Ne1",
    page: 74,
    initial: "d4 Nf6 c4 g6 Nc3 Bg7 e4 d6 Nf3 O-O Be2 e5 O-O Nc6 d5 Ne7 b4 Nh5 Re1 Nf4 Bf1 f5 Bxf4 exf4 e5",
    moves: [
      { m: "dxe5", c: "Gallagher accepts the transaction, opening critical center positions." },
      { m: "Rxe5", c: "White's active rook recaptures, dominating the central corridor." },
      { m: "Nc6", c: "Black immediately attacks the active white rook, forcing a response." },
      { m: "Re1", c: "The rook retreats, maintaining solid development." }
    ]
  },
  {
    num: 28,
    white: "Ljubojevic",
    black: "Kasparov",
    event: "Linares",
    year: 1993,
    chapter: 4,
    chapterTitle: "7 O-O Nc6: Alternatives to 9 Ne1",
    page: 76,
    initial: "d4 Nf6 c4 g6 Nc3 Bg7 e4 d6 Nf3 O-O Be2 e5 O-O Nc6 d5 Ne7 Ne1 Nd7 Nd3 f5 Bd2 Nf6 f3 f4 c5 g5 Rc1 Ng6 cxd6 cxd6 Nb5 Rf7 Qc2 Ne8 a4 h5 Nf2 Bf8 a5 Bd7 Qb3 Rg7 h3 Nh4 Rc3 a6 Na3",
    moves: [
      { m: "g4", c: "Kasparov unleashes the g4 pawn thrust, initiating a fierce kingside storm." },
      { m: "fxg4", c: "White recaptures on g4, but this only serves to open up the lines of attack." },
      { m: "hxg4", c: "Kasparov immediately trades, opening up the h-file for the attacking rooks." },
      { m: "hxg4", c: "White recaptures on g4 to restore material balance, though the kingside remains vulnerable." },
      { m: "b5", c: "A beautiful queenside response! Challenging White's structural alignment and creating dynamic counter-thrusts." }
    ]
  },
  {
    num: 29,
    white: "Kramnik",
    black: "Shirov",
    event: "Bundesliga",
    year: 1992,
    chapter: 5,
    chapterTitle: "The Sämisch Variation",
    page: 83,
    initial: "d4 Nf6 c4 g6 Nc3 Bg7 e4 d6 f3 O-O Be3 e5 Nge2 c6 Qd2 Nbd7 d5 cxd5 cxd5 a6 g4 h5 h3 Nh7",
    moves: [
      { m: "O-O-O", c: "Kramnik castles queenside, committing to an opposite-side castling attack." },
      { m: "hxg4", c: "Shirov strikes immediately! Blowing open the h-file before White's attack gets rolling." },
      { m: "hxg4", c: "Trade. White accepts the open file but gains isolated pawn weaknesses." },
      { m: "Qh4", c: "The black queen lands with immense power on the kingside." }
    ]
  },
  {
    num: 30,
    white: "Dreyer",
    black: "Watanabe",
    event: "Yerevan Olympiad",
    year: 1996,
    chapter: 5,
    chapterTitle: "The Sämisch Variation",
    page: 83,
    initial: "d4 Nf6 c4 g6 Nc3 Bg7 e4 d6 f3 O-O Be3 e5 Nge2 c6 Qd2 Nbd7 O-O-O a6 Kb1 b5 Nc1 exd4 Bxd4",
    moves: [
      { m: "Re8", c: "Developing the rook on the e-file, targeting the central e4 complex." },
      { m: "g4", c: "White rolls the kingside pawns, seeking to start a severe king-hunt." },
      { m: "Ne5", c: "Black snaps a strong central coordinate, putting pressure on f3 and g4." },
      { m: "Bxe5", c: "White trade. Relieving central pressure before things get too wild." }
    ]
  },
  {
    num: 31,
    white: "Belotti",
    black: "M. Piket",
    event: "Lugano",
    year: 1989,
    chapter: 5,
    chapterTitle: "The Sämisch Variation",
    page: 85,
    initial: "d4 Nf6 c4 g6 Nc3 Bg7 e4 d6 f3 O-O Be3 e5 Nge2 c6 Qd2 Nbd7 d5 cxd5 cxd5 a6 O-O-O b5 Kb1 Nb6",
    moves: [
      { m: "Nc1", c: "White repositions the knight to cover weaknesses on the queenside light squares." },
      { m: "Nc4", c: "Black's active knight targets b2 and d2, keeping White's pieces tied down." },
      { m: "Bxc4", c: "White is forced to trade their bishop for the powerful knight on c4." },
      { m: "bxc4", c: "Recaptured. Black gains a massive queenside pawn majority and open files." }
    ]
  },
  {
    num: 32,
    white: "Rivas",
    black: "Mestel",
    event: "Marbella",
    year: 1982,
    chapter: 5,
    chapterTitle: "The Sämisch Variation",
    page: 88,
    initial: "d4 Nf6 c4 g6 Nc3 Bg7 e4 d6 f3 O-O Be3 e5 d5 Nh5 Qd2 Qh4+ g3 Qe7 O-O-O f5",
    moves: [
      { m: "Bd3", c: "White develops the bishop to d3, reinforcing the center and preparing coordinates." },
      { m: "Na6", c: "Mestel plays Na6, preparing to jump to c5 or b4 to create threats." },
      { m: "Nge2", c: "Developing the knight to e2, maintaining central balance and safety." },
      { m: "f4", c: "Black continues expanding on the kingside to challenge White's setup." }
    ]
  },
  {
    num: 33,
    white: "Muir",
    black: "Fedorov",
    event: "European Team Ch, Batumi",
    year: 1999,
    chapter: 5,
    chapterTitle: "The Sämisch Variation",
    page: 90,
    initial: "d4 Nf6 c4 g6 Nc3 Bg7 e4 d6 f3 O-O Be3 e5 d5 Nh5 Qd2 f5 Nge2 f4 Bf2 Bf6",
    moves: [
      { m: "g3", c: "White tries to stop the kingside pawn expansion, locking the structure." },
      { m: "g5", c: "Fedorov is having none of it! Pushing g5 to roll over the defensive line." },
      { m: "gxf4", c: "White trades to open lines, hoping for tactical counterplay." },
      { m: "Nxf4", c: "Black recaptures with the knight, occupying a brilliant central outpost." }
    ]
  },
  {
    num: 34,
    white: "Michenka",
    black: "Hagara",
    event: "Trinec",
    year: 1998,
    chapter: 5,
    chapterTitle: "The Sämisch Variation",
    page: 91,
    initial: "d4 Nf6 c4 g6 Nc3 Bg7 e4 d6 f3 O-O Be3 e5 d5 c5 Qd2 Ne8 g4",
    moves: [
      { m: "f5", c: "Black immediately strikes back in the center, refusing to be passive." },
      { m: "exf5", c: "Trade. White aims to open key paths on the e-file." },
      { m: "Bxf5", c: "Recaptured. Black activates the light-squared bishop, seizing key diagonals." },
      { m: "O-O-O", c: "White castles queenside, setting the stage for opposite-side tactical attacks." }
    ]
  },
  {
    num: 35,
    white: "Istratescu",
    black: "Akopian",
    event: "European Ch, Ohrid",
    year: 2001,
    chapter: 5,
    chapterTitle: "The Sämisch Variation",
    page: 95,
    initial: "d4 Nf6 c4 g6 Nc3 Bg7 e4 d6 f3 O-O Be3 c6 Bd3 a6 Nge2 b5 e5 Nfd7 f4 bxc4 Bxc4 Nb6",
    moves: [
      { m: "Bb3", c: "The bishop retreats to a safe active outpost on b3, keeping an eye on f7." },
      { m: "a5", c: "Black expands with ...a5, threatening to disturb White's queenside structure." },
      { m: "O-O", c: "White castles safely, preparing to initiate center blockades." },
      { m: "Ba6", c: "Deploying the bishop with tempo, pinning or restricting White's pieces." }
    ]
  },
  {
    num: 36,
    white: "A. Kuzmin",
    black: "Sakaev",
    event: "Doha",
    year: 1993,
    chapter: 5,
    chapterTitle: "The Sämisch Variation",
    page: 96,
    initial: "d4 Nf6 c4 g6 Nc3 Bg7 e4 d6 f3 O-O Be3 c6 Bd3 a6 Nge2 b5 O-O Nbd7 Rc1 e5 d5 cxd5 cxd5 Nc5",
    moves: [
      { m: "Bb1", c: "White retreats the bishop to b1, maintaining control over the active diagonal." },
      { m: "b4", c: "Black kicks the c3 knight, securing space and queenside advantage." },
      { m: "Na4", c: "The knight jumps to a4, targeting the weak b2/c3 coordinate." },
      { m: "Nfd7", c: "White defends by routing the knight back to protect the queenside." }
    ]
  },
  {
    num: 37,
    white: "Hauchard",
    black: "Krakops",
    event: "Cappelle la Grande",
    year: 1997,
    chapter: 5,
    chapterTitle: "The Sämisch Variation",
    page: 99,
    initial: "d4 Nf6 c4 g6 Nc3 Bg7 e4 d6 f3 O-O Be3 e5 Nge2 c6 Qd2 Nbd7 d5 cxd5 cxd5 a6 a4 Nh7",
    moves: [
      { m: "g4", c: "An aggressive thrust! White pushes g4 to restrict Black's minor pieces." },
      { m: "h5", c: "Black immediately challenges the pawn hook, attempting to open lines." },
      { m: "h3", c: "Solidifying the g4 pawn, maintaining the kingside wall." },
      { m: "hxg4", c: "Black opens the h-file to prepare active plans for the heavy pieces." }
    ]
  },
  {
    num: 38,
    white: "Rogers",
    black: "Gallagher",
    event: "Lugano",
    year: 1999,
    chapter: 5,
    chapterTitle: "The Sämisch Variation",
    page: 100,
    initial: "d4 Nf6 c4 g6 Nc3 Bg7 e4 d6 f3 O-O Be3 c5 d5 e6 Qd2 exd5 cxd5 a6 a4 h6 Nge2 Nbd7 Ng3 Ne5 Be2",
    moves: [
      { m: "Bxh6", c: "White tries 14. Bxh6, but is met by a devastating counter-thrust!" },
      { m: "Nxe4", c: "A brilliant central blow! Exposing White's center and starting a double-attack." },
      { m: "Nxe4", c: "Trade. Now the black queen joins with check." },
      { m: "Qh4+", c: "Check! This wins the newly-placed h6 bishop on the next move, leaving Black with a winning edge." }
    ]
  },
  {
    num: 39,
    white: "Hohler",
    black: "Gallagher",
    event: "Bern",
    year: 1994,
    chapter: 6,
    chapterTitle: "The Fianchetto Variation",
    page: 105,
    initial: "d4 Nf6 c4 g6 Nf3 Bg7 g3 O-O Bg2 d6 Nc3 Nbd7 O-O e5 e4 c6 h3 Qb6 c5 dxc5 dxe5 Ne8",
    moves: [
      { m: "e6", c: "White pushes e6, trying to cramp Black's development and seal the f8-bishop." },
      { m: "fxe6", c: "Recaptured safely. The f-file becomes active for Black." },
      { m: "Qc2", c: "Centralizing the White queen, keeping an eye on key coordinates." },
      { m: "Nc7", c: "Black's knight maneuvers to support the center e5 and blockades White's pawns." }
    ]
  },
  {
    num: 40,
    white: "Whiteley",
    black: "Gallagher",
    event: "Royan",
    year: 1989,
    chapter: 6,
    chapterTitle: "The Fianchetto Variation",
    page: 106,
    initial: "d4 Nf6 c4 g6 Nf3 Bg7 g3 O-O Bg2 d6 Nc3 Nbd7 O-O e5 e4 c6 h3 Qb6 Re1 exd4 Nxd4 Re8 Re2 Nc5",
    moves: [
      { m: "Be3", c: "White develops the bishop, setting up a potential tactical discovery on Black's queen." },
      { m: "Qd8", c: "Black's queen steps back safely to d8, neutralizing the discovery threat." },
      { m: "Qc2", c: "White centralizes the queen, ready to connect rooks on the d-file." },
      { m: "a5", c: "Black gains space on the queenside, preparing to secure the c5-knight's outpost." }
    ]
  },
  {
    num: 41,
    white: "Schwartzman",
    black: "Nisipeanu",
    event: "Bucharest",
    year: 1994,
    chapter: 6,
    chapterTitle: "The Fianchetto Variation",
    page: 108,
    initial: "d4 Nf6 c4 g6 Nf3 Bg7 g3 O-O Bg2 d6 Nc3 Nbd7 O-O e5 e4 c6 h3 Qb6 Re1 exd4 Nxd4 Re8 Nb3 Qb4 Bf1 Ne5",
    moves: [
      { m: "a3", c: "White kicks the black queen with 16. a3, attempting to gain a tempo." },
      { m: "Qb6", c: "The queen retreats to b6, keeping pressure on White's queenside structure." },
      { m: "Be3", c: "White continues expanding with tempi, attacking the queen." },
      { m: "Qc7", c: "The queen lands on c7, preparing a robust positional defense." }
    ]
  },
  {
    num: 42,
    white: "Filippov",
    black: "Sepp",
    event: "Novgorod",
    year: 1995,
    chapter: 6,
    chapterTitle: "The Fianchetto Variation",
    page: 110,
    initial: "d4 Nf6 c4 g6 Nf3 Bg7 g3 O-O Bg2 d6 Nc3 Nbd7 O-O e5 e4 c6 h3 Qb6 Re1 exd4 Nxd4 Re8 Re2 Nc5 Bf4 a5",
    moves: [
      { m: "Bxd6", c: "White captures a free central pawn, but this exposes the queenside light squares." },
      { m: "Nfd7", c: "Black re-routes the knight to challenge White's active e4 pawn." },
      { m: "Bf4", c: "White's bishop retreats to f4, solidifying the central defensive camp." },
      { m: "a4", c: "Black seeks counterplay, aiming to lock White's queenside options." }
    ]
  },
  {
    num: 43,
    white: "Filippov",
    black: "Lyrberg",
    event: "Minsk",
    year: 1996,
    chapter: 6,
    chapterTitle: "The Fianchetto Variation",
    page: 112,
    initial: "d4 Nf6 c4 g6 Nf3 Bg7 g3 O-O Bg2 d6 Nc3 Nbd7 O-O e5 e4 c6 h3 Qb6 Re1 exd4 Nxd4 Re8 Nc2 Nc5 Re2 Be6",
    moves: [
      { m: "b3", c: "White solidifies the vital c4 pawn, but now the a1 rook is slightly exposed." },
      { m: "Rad8", c: "Black places a rook on the d-file, preparing a central e5-e4 blowout." },
      { m: "Qe1", c: "White shifts the queen to avoid any tactical x-ray attacks on the d-file." },
      { m: "Bc8", c: "Black retreats the bishop to safety, resetting the offensive coordinate." }
    ]
  },
  {
    num: 44,
    white: "Yusupov",
    black: "Kindermann",
    event: "Baden Baden",
    year: 1992,
    chapter: 6,
    chapterTitle: "The Fianchetto Variation",
    page: 116,
    initial: "d4 Nf6 c4 g6 Nf3 Bg7 g3 O-O Bg2 d6 Nc3 Nbd7 O-O e5 b3 Re8 Bb2 c6 e4 exd4 Nxd4 a5",
    moves: [
      { m: "Re1", c: "White centralizes the rook, reinforcing the e4 pawn." },
      { m: "Nc5", c: "Developing the knight to c5, targeting the e4 pawn and getting ready for queenside action." },
      { m: "h3", c: "Preventing any annoying ...Ng4 jumps from Black." },
      { m: "Qb6", c: "Black develops the queen with pressure, targeting the b3 and f2 squares." }
    ]
  },
  {
    num: 45,
    white: "Partenheimer",
    black: "Nunn",
    event: "Bundesliga",
    year: 2001,
    chapter: 6,
    chapterTitle: "The Fianchetto Variation",
    page: 117,
    initial: "d4 Nf6 c4 g6 Nf3 Bg7 g3 O-O Bg2 d6 Nc3 Nbd7 O-O e5 b3 Re8 dxe5 dxe5 e4 c6 Ba3 Bf8",
    moves: [
      { m: "Bxf8", c: "White swaps bishops, liquidating Black's dark-square defender." },
      { m: "Kxf8", c: "John Nunn recaptures with the King, securing a safe royal coordinate." },
      { m: "Qd6", c: "The White queen penetrates, occupying a strong positional square." },
      { m: "Qe7", c: "Black challenges the queen, offering to trade and neutralize the attack." }
    ]
  },
  {
    num: 46,
    white: "Arkell",
    black: "Buckley",
    event: "South Wales Masters",
    year: 2001,
    chapter: 6,
    chapterTitle: "The Fianchetto Variation",
    page: 119,
    initial: "d4 Nf6 c4 g6 Nf3 Bg7 g3 O-O Bg2 d6 Nc3 Nbd7 O-O e5 b3 Re8 Bb2 c6 h3 a5 e3 exd4 Nxd4",
    moves: [
      { m: "Nc5", c: "The knight lands on c5, targeting the e4 pawn and putting pressure on White's base." },
      { m: "Qc2", c: "White centralizes the queen, ready to reinforce the e4 pawn." },
      { m: "Bd7", c: "Developing the bishop to d7, preparing for heavy rooks to coordinate on the b-file." },
      { m: "Rad1", c: "White counters with a central rook on the open d-file." }
    ]
  },
  {
    num: 47,
    white: "Banikas",
    black: "Gallagher",
    event: "French League",
    year: 2001,
    chapter: 7,
    chapterTitle: "The Four Pawns Attack",
    page: 123,
    initial: "d4 Nf6 c4 g6 Nc3 Bg7 e4 d6 f4 O-O Nf3 c5 d5 e6 Be2 exd5 cxd5 Bg4 O-O Nbd7 h3 Bxf3 Bxf3",
    moves: [
      { m: "Re8", c: "Black targets the e4 pawn on the open e-file, launching strong pressure on White's center." },
      { m: "Re1", c: "White defends the critical e4 pawn, keeping their massive center intact." },
      { m: "a6", c: "Preparing queenside expansion with ...b7-b5 to challenge White's spatial advantage." },
      { m: "a4", c: "White blocks Black's queenside expansion, but slightly weakens their own b4 square." }
    ]
  },
  {
    num: 48,
    white: "Vaisser",
    black: "Bauer",
    event: "French Cup",
    year: 1992,
    chapter: 7,
    chapterTitle: "The Four Pawns Attack",
    page: 126,
    initial: "d4 Nf6 c4 g6 Nc3 Bg7 e4 d6 f4 O-O Nf3 c5 d5 e6 Be2 exd5 cxd5 Re8 Nd2 Na6 O-O Nc7 a4 b6",
    moves: [
      { m: "Re1", c: "White solidifies the e4 pawn, ready to absorb any upcoming tactics on the e-file." },
      { m: "Ba6", c: "The black bishop finds a beautiful active post on a6, targeting White's key coordinates." },
      { m: "Bxa6", c: "White is forced to trade, liquidating Black's active bishop." },
      { m: "Nxa6", c: "Black recaptures with the knight, keeping an incredibly active, dynamic game." }
    ]
  },
  {
    num: 49,
    white: "Blokh",
    black: "Kichev",
    event: "corr USSR",
    year: 1991,
    chapter: 7,
    chapterTitle: "The Four Pawns Attack",
    page: 127,
    initial: "d4 Nf6 c4 g6 Nc3 Bg7 e4 d6 f4 O-O Nf3 c5 d5 e6 Be2 exd5 cxd5 Re8 e5 dxe5 fxe5 Ng4 Bg5 Qb6 O-O",
    moves: [
      { m: "Nxe5", c: "An active challenge! Black snaps the central pawn on e5, initiating a sharp tactical battle." },
      { m: "Nxe5", c: "White trades back. Keeping piece activity equal." },
      { m: "Bxe5", c: "Black's bishop recaptures on e5, becoming an extremely strong and active piece on the main diagonal." },
      { m: "Bf4", c: "White develops their bishop, seeking active counterplay on the light squares." }
    ]
  },
  {
    num: 50,
    white: "Conquest",
    black: "Mestel",
    event: "Hastings",
    year: 1986,
    chapter: 7,
    chapterTitle: "The Four Pawns Attack",
    page: 130,
    initial: "d4 Nf6 c4 g6 Nc3 Bg7 e4 d6 f4 O-O Nf3 c5 d5 e6 Be2 exd5 cxd5 Bg4 O-O Nbd7 e5 dxe5 fxe5 Ne8 Bf4 Bxf3 Bxf3 Bxe5",
    moves: [
      { m: "Bxe5", c: "White trades bishops on e5, liquidating Black's active defender." },
      { m: "Nxe5", c: "Black recaptures with the knight, establishing a solid central outpost." },
      { m: "Qe2", c: "White centralizes the queen, ready to reinforce their central setup." },
      { m: "Nd6", c: "The black knight steps back to d6, blockading White's pawn expansion." }
    ]
  },
  {
    num: 51,
    white: "I. Sokolov",
    black: "Xie Jun",
    event: "Dutch Team Ch",
    year: 1999,
    chapter: 7,
    chapterTitle: "The Four Pawns Attack",
    page: 132,
    initial: "d4 Nf6 c4 g6 Nc3 Bg7 e4 d6 f4 O-O Nf3 c5 d5 e6 Be2 exd5 cxd5 Re8 e5 dxe5 fxe5 Ng4 Bg5 Qb6 Qd2 Nxe5 Nxe5 Bxe5",
    moves: [
      { m: "O-O-O", c: "Sokolov castles queenside, committing to a sharp opposite-side attacking battle." },
      { m: "Bf5", c: "Black activates the light-squared bishop, seizing key diagonals on the kingside." },
      { m: "g4", c: "White immediately rolls the g-pawn to kick Black's bishop and start a pawn storm." },
      { m: "Bc8", c: "The bishop retreats safely, but Black's dynamic game remains highly active." }
    ]
  },
  {
    num: 52,
    white: "Ca. Hansen",
    black: "Berg",
    event: "Aarhus",
    year: 1991,
    chapter: 7,
    chapterTitle: "The Four Pawns Attack",
    page: 134,
    initial: "d4 Nf6 c4 g6 Nc3 Bg7 e4 d6 f4 O-O Nf3 c5 d5 e6 Be2 exd5 cxd5 Bg4 O-O Bxf3 Bxf3 Nbd7",
    moves: [
      { m: "Kh1", c: "Slipping the King to a safe corner square, avoiding potential tactical checks on the a1-h8 diagonal." },
      { m: "Re8", c: "Black targets the e4 pawn on the open e-file, launching strong pressure." },
      { m: "Re1", c: "White defends the critical e4 pawn, keeping their massive center intact." },
      { m: "Qc7", c: "Black centralizes the queen, coordinating the minor units beautifully." }
    ]
  },
  {
    num: 53,
    white: "Parker",
    black: "Gallagher",
    event: "British League, Birmingham",
    year: 2001,
    chapter: 7,
    chapterTitle: "The Four Pawns Attack",
    page: 136,
    initial: "d4 Nf6 c4 g6 Nc3 Bg7 e4 d6 f4 O-O Nf3 c5 d5 e6 Be2 exd5 cxd5 Re8 e5 dxe5 fxe5 Ng4 Bf4 Nxe5 O-O",
    moves: [
      { m: "Nxf3+", c: "Black trades knights on f3 to resolve space tensions." },
      { m: "Bxf3", c: "White's bishop recaptures on f3, becoming an extremely strong and active piece." },
      { m: "Nd7", c: "Black brings the knight out to support the solid center." },
      { m: "Qd2", c: "White centralizes the queen, preparing to coordinate their minor forces." }
    ]
  },
  {
    num: 54,
    white: "Videki",
    black: "Gallagher",
    event: "Kecskemet",
    year: 1990,
    chapter: 7,
    chapterTitle: "The Four Pawns Attack",
    page: 137,
    initial: "d4 Nf6 c4 g6 Nc3 Bg7 e4 d6 f4 O-O Nf3 c5 d5 e6 Be2 exd5 cxd5 Re8 e5 dxe5 fxe5 Ng4 Bg5 Qb6 h3",
    moves: [
      { m: "Nf6", c: "The knight retreats, keeping an eye on the defensive squares on the kingside." },
      { m: "Bc4", c: "White develops the bishop to a strong active outpost on c4, targeting f7." },
      { m: "exd5", c: "Black trades pawns in the center, trying to clear files." },
      { m: "Nxd5", c: "White's knight recaptures, maintaining spatial pressure." }
    ]
  },
  {
    num: 55,
    white: "Milov",
    black: "Shchekachev",
    event: "Amsterdam",
    year: 2000,
    chapter: 8,
    chapterTitle: "The Averbakh Variation",
    page: 142,
    initial: "d4 Nf6 c4 g6 Nc3 Bg7 e4 d6 Be2 O-O Bg5 c5 d5 e6 Qd2 exd5 exd5 Re8 Nf3 Bg4 O-O Bxf3 Bxf3 Nbd7",
    moves: [
      { m: "Rae1", c: "White centralizes the rook, reinforcing the e1-e4 central corridor beautifully." },
      { m: "Rxe1+", c: "Black trades rooks, trying to reduce White's major piece pressure." },
      { m: "Rxe1", c: "White recaptures with the rook, maintaining control of the open e-file." },
      { m: "a6", c: "Black expands on the queenside, preparing to secure their minor units." }
    ]
  },
  {
    num: 56,
    white: "Bareev",
    black: "Akopian",
    event: "Moscow",
    year: 1989,
    chapter: 8,
    chapterTitle: "The Averbakh Variation",
    page: 143,
    initial: "d4 Nf6 c4 g6 Nc3 Bg7 e4 d6 Be2 O-O Bg5 h6 Be3 e5 d5 Na6 Qd2 Nc5 f3 a5 Bd1 Nh5 Nge2 Qh4+ g3 Qe7",
    moves: [
      { m: "Bc2", c: "Developing the bishop to Bc2, aiming to support the queenside b4-c4 push." },
      { m: "f5", c: "Akopian challenges the center beautifully with f5, launching a kingside storm." },
      { m: "exf5", c: "White exchanges pawns to open up files for their active rooks." },
      { m: "gxf5", c: "Black recaptures toward the center, accepting open attacking files." }
    ]
  },
  {
    num: 57,
    white: "Ioseliani",
    black: "Gallagher",
    event: "Biel",
    year: 1990,
    chapter: 8,
    chapterTitle: "The Averbakh Variation",
    page: 146,
    initial: "d4 Nf6 c4 g6 Nc3 Bg7 e4 d6 Be2 O-O Bg5 c5 d5 e6 Qd2 exd5 exd5 Re8 Nf3 Bf5 O-O Nbd7 Rae1 Qb6",
    moves: [
      { m: "Nh4", c: "An active jump! White immediately leaps to challenge Black's active light-squared bishop." },
      { m: "Ne4!", c: "Superb! Black plays ...Ne4, launching a powerful central double-attack on White's d2 queen." },
      { m: "Nxe4", c: "Trade. White captures the knight to avoid immediate material loss." },
      { m: "Bxe4", c: "Recaptured. Black's bishop becomes extremely strong and active in the center." }
    ]
  },
  {
    num: 58,
    white: "S. Mohr",
    black: "Uhlmann",
    event: "Bundesliga",
    year: 1995,
    chapter: 8,
    chapterTitle: "The Averbakh Variation",
    page: 148,
    initial: "d4 Nf6 c4 g6 Nc3 Bg7 e4 d6 Be2 O-O Bg5 Na6 Qd2 e5 d5 Qe8 Bd1 Nc5 f3 a5 Nge2 Nh5",
    moves: [
      { m: "g4", c: "An aggressive thrust! White pushes g4, aiming to restrict Black's minor pieces on the kingside." },
      { m: "Nf4", c: "Black immediately jumps on the opportunity, centralizing the knight beautifully." },
      { m: "Nxf4", c: "White trades. Keeping piece activity equal." },
      { m: "exf4", c: "Black recaptures toward the center, opening up lines for attacking play." }
    ]
  },
  {
    num: 59,
    white: "Zlotnikov",
    black: "Gallagher",
    event: "Arosa",
    year: 1996,
    chapter: 9,
    chapterTitle: "White Plays an Early h2-h3",
    page: 153,
    initial: "d4 Nf6 c4 g6 Nc3 Bg7 e4 d6 h3 O-O Bg5 Na6 Nf3 e5 d5 Qe8 Be2 Nh5 g3 f5 exf5 gxf5",
    moves: [
      { m: "Nh4", c: "White attacks the h5 knight, forcing a defensive response on the kingside." },
      { m: "Nf6", c: "The knight retreats to f6, maintaining dynamic stability and coordination." },
      { m: "Qc2", c: "White centralizes the queen, ready to reinforce their central setup." },
      { m: "e4", c: "Black strikes beautifully in the center, gaining space and active counterplay." }
    ]
  },
  {
    num: 60,
    white: "Agrest",
    black: "Milov",
    event: "European Ch, Ohrid",
    year: 2001,
    chapter: 9,
    chapterTitle: "White Plays an Early h2-h3",
    page: 155,
    initial: "d4 Nf6 c4 g6 Nc3 Bg7 e4 d6 h3 O-O Bg5 c5 d5 e6 Bd3 exd5 exd5 Re8+ Nge2 Nbd7 f4 h6 Bh4 Nf8",
    moves: [
      { m: "O-O", c: "White castles safely, committing to a solid positional setup." },
      { m: "a6", c: "Black prepares queenside expansion with ...b7-b5 to challenge White's spatial advantage." },
      { m: "a4", c: "White blocks Black's queenside expansion, but slightly weakens their own b4 square." },
      { m: "Qc7", c: "Black centralizes the queen, coordinating the minor units beautifully." }
    ]
  },
  {
    num: 61,
    white: "Krasenkov",
    black: "Andonovski",
    event: "Panormo",
    year: 2001,
    chapter: 9,
    chapterTitle: "White Plays an Early h2-h3",
    page: 158,
    initial: "d4 Nf6 c4 g6 Nc3 Bg7 e4 d6 h3 O-O Be3 Ne8 g4 e5 d5 f5 gxf5 gxf5 exf5 Bxf5 Nge2 Nd7",
    moves: [
      { m: "Ng3", c: "White jumps the knight to g3, putting immediate blockading pressure on the f5 bishop." },
      { m: "Bg6", c: "The bishop retreats safely to g6, maintaining its active diagonal control." },
      { m: "h4", c: "An aggressive thrust! White pushes h4, aiming to lock Black's kingside pawn hook." },
      { m: "Nef6", c: "Black brings the knight out to support the solid center." }
    ]
  },
  {
    num: 62,
    white: "J. Ivanov",
    black: "V. Georgiev",
    event: "Salou",
    year: 2000,
    chapter: 9,
    chapterTitle: "White Plays an Early h2-h3",
    page: 159,
    initial: "d4 Nf6 c4 g6 Nc3 Bg7 e4 d6 h3 O-O Bg5 Na6 Nf3 e5 d5 Qe8 Be2 Nh5 Qd2 f5 exf5 gxf5",
    moves: [
      { m: "O-O-O", c: "White castles queenside, committing to a sharp opposite-side castling attack." },
      { m: "Qg6", c: "Black centralizes the queen, ready to coordinate their minor forces." },
      { m: "g3", c: "White solidifies their kingside structure, preventing any tactical surprises." },
      { m: "f4", c: "Black strikes beautifully in the center, gaining space and active counterplay." }
    ]
  },
  {
    num: 63,
    white: "Kabalek",
    black: "Kasparov",
    event: "Bugojno",
    year: 1982,
    chapter: 9,
    chapterTitle: "White Plays an Early h2-h3",
    page: 161,
    initial: "d4 Nf6 c4 g6 Nc3 Bg7 e4 d6 h3 O-O Bg5 c5 d5 e6 Bd3 exd5 exd5 Re8+ Nge2 Na6 O-O Nc7 a4",
    moves: [
      { m: "b6", c: "Solidifying the queenside structure, preparing to develop the light-squared bishop." },
      { m: "Qd2", c: "White centralizes the queen, ready to coordinate their minor forces." },
      { m: "Ba6", c: "Developing the bishop to a6, targeting White's key coordinates." },
      { m: "Rfe1", c: "White centralizes the rook, maintaining control of the open e-file." }
    ]
  },
  {
    num: 64,
    white: "Piket",
    black: "Fedorov",
    event: "Wijk aan Zee",
    year: 2001,
    chapter: 10,
    chapterTitle: "Other Systems",
    page: 165,
    initial: "d4 Nf6 c4 g6 Nc3 Bg7 e4 d6 Be3 O-O Be2 e5 d5 a5 h4 Na6 h5 Nc5",
    moves: [
      { m: "hxg6", c: "White exchanges on g6, opening the h-file for their attacking heavy pieces." },
      { m: "fxg6", c: "Recaptured. Black opens the f-file for their active rooks." },
      { m: "f3", c: "White solidifies their kingside structure, preventing any tactical surprises." },
      { m: "c6", c: "Black strikes beautifully in the center, challenging White's spatial advantage." }
    ]
  },
  {
    num: 65,
    white: "Liardet",
    black: "Peng Xiaomin",
    event: "Geneva",
    year: 1997,
    chapter: 10,
    chapterTitle: "Other Systems",
    page: 168,
    initial: "d4 Nf6 c4 g6 Nc3 Bg7 e4 d6 Be3 O-O Be2 e5 d5 a5 Nf3 Na6 Nd2 Nd7 g4 Ndc5 h4",
    moves: [
      { m: "f5", c: "Peng Xiaomin responds aggressively, pushing f5 to roll over the defensive line." },
      { m: "gxf5", c: "White trades to open lines, hoping for tactical counterplay." },
      { m: "Bxf5", c: "Black recaptures with the bishop, activating their minor forces." },
      { m: "h5", c: "White pushes h5, trying to lock Black's kingside pawn hook." }
    ]
  },
  {
    num: 66,
    white: "Liardet",
    black: "Gallagher",
    event: "Lenk",
    year: 1998,
    chapter: 10,
    chapterTitle: "Other Systems",
    page: 168,
    initial: "d4 Nf6 c4 g6 Nc3 Bg7 e4 d6 Be3 O-O Be2 e5 d5 a5 Nf3 Na6 Nd2 Nd7 g4 Ndc5 h4 Bd7",
    moves: [
      { m: "h5", c: "White pushes h5, trying to lock Black's kingside pawn hook." },
      { m: "f5", c: "Gallagher strikes back immediately in the center, refusing to be passive." },
      { m: "exf5", c: "Trade. White aims to open key paths on the e-file." },
      { m: "Bxf5", c: "Black recaptures with the bishop, activating all minor units beautifully." }
    ]
  },
  {
    num: 67,
    white: "Sharif",
    black: "Mamedov",
    event: "Abu Dhabi",
    year: 2001,
    chapter: 10,
    chapterTitle: "Other Systems",
    page: 172,
    initial: "d4 Nf6 c4 g6 Nc3 Bg7 e4 d6 Be3 O-O Be2 e5 d5 a5 Nf3 Na6 Nd2 Nd7 O-O f5",
    moves: [
      { m: "exf5", c: "White exchanges on f5, seeking to limit Black's kingside mating network." },
      { m: "gxf5", c: "Black recaptures toward the center, accepting open attacking files." },
      { m: "f4", c: "White counters with f4, attempting to challenge Black's central control." },
      { m: "exf4", c: "Black takes the central pawn, shattering White's pawn structure." }
    ]
  },
  {
    num: 68,
    white: "Pachman",
    black: "Smyslov",
    event: "Amsterdam",
    year: 1994,
    chapter: 10,
    chapterTitle: "Other Systems",
    page: 173,
    initial: "d4 Nf6 c4 g6 Nc3 Bg7 e4 d6 Be2 O-O Be3 e5 d5 a5 Nf3 Na6 Nd2 Nd7 O-O f5 exf5 gxf5 f4 Ndc5",
    moves: [
      { m: "fxe5", c: "White trades on e5, hoping to resolve space tensions." },
      { m: "dxe5", c: "Smyslov recaptures safely, maintaining a strong footprint in the center." },
      { m: "Qxd8", c: "The queens are traded off, transitioning smoothly into an instructive endgame." },
      { m: "Rxd8", c: "Smyslov recaptures the queen, completing the trade." },
      { m: "Nf3", c: "White develops their knight, seeking active counterplay." }
    ]
  }
];

export function getFullIllustrativeGamesList(): SampleBookPage[] {
  return COMPACT_68_GAMES.map(g => {
    // Generate moves chronology with correct player color alternates
    const movesList: ChessMove[] = [];
    const initialMovesList = g.initial 
      ? g.initial.trim().split(/\s+/).filter(token => !/^\d+$/.test(token)) 
      : [];
    const initialMovesCount = initialMovesList.length;
    let isWhiteTurn = initialMovesCount % 2 === 0;
    let currentMoveNumber = Math.floor(initialMovesCount / 2) + 1;
    const startingMove = currentMoveNumber;

    g.moves.forEach((mv, idx) => {
      movesList.push({
        move_number: currentMoveNumber,
        player: isWhiteTurn ? 'W' : 'B',
        move: mv.m,
        commentary: mv.c
      });

      if (!isWhiteTurn) {
        currentMoveNumber++;
      }
      isWhiteTurn = !isWhiteTurn;
    });

    const pageId = `game_${g.num}`;

    return {
      id: pageId,
      title: `Game ${g.num}: ${g.white} vs ${g.black} (${g.event} ${g.year})`,
      description: `Chapter ${g.chapter} (${g.chapterTitle}) • Page ${g.page}`,
      imageFilename: "chess_board.png",
      textContext: `Game ${g.num}
White: ${g.white}
Black: ${g.black}
Event: ${g.event} ${g.year}
Page: ${g.page}

Initial Setup: ${g.initial}

Moves:
${g.moves.map((m, i) => `${i + 1}. ${m.m} - ${m.c}`).join('\n')}`,
      preparsedJson: {
        game_id: pageId,
        white: g.white,
        black: g.black,
        event: `${g.event} ${g.year}`,
        initial_moves: g.initial,
        interactive_section: {
          starting_move: startingMove,
          moves: movesList
        }
      }
    };
  });
}
