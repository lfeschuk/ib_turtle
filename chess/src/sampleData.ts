import { SampleBookPage } from './types';
import { COMPLED_EXERCISES } from './preparsedBookData';
import { getFullIllustrativeGamesList } from './all68GamesData';

// Combine the 11 high-quality interactive exercises with the complete 68 illustrative games list
const illustrativeGames = getFullIllustrativeGamesList();

export const SAMPLE_PAGES: SampleBookPage[] = [
  ...COMPLED_EXERCISES,
  ...illustrativeGames,
  {
    id: 'game_1_tactical_trap',
    title: 'Bonus-Tactics: The Classical Variation Trap',
    description: 'The tactical fragment from Chapter 1 showing White playing the risky 16 O-O-O and falling into a vicious bishop-mating net.',
    imageFilename: 'chess_board.png',
    textContext: `14...Nc5 15 Nc4?!
A slight mistake as it allows Black some tricks based on ...Nxe4, while the knight may also get booted by ..b7-b5 at some point.
Best is 15 O-O-O! and after 15...Ne6! ... lead to equality.
15...Bf8
This keeps the knight out of d6 and also transfers the bishop to a more active post. There is not much life on the long diagonal.
16 O-O-O
On the last move castling queenside was best. Now it is rather risky.
16...Be6 17 Kb1 Rac8
17...Nxe4 18 Bxe4 Bxc4 19 Bxb7 Rab8 is fine for Black but I wanted more. I saw a sneaky way to improve this line.
18 Be3?
Thank you very much. White falls for the trap. He should have played 18 Rhe1 when 18...Bxd5 19 exd5 should be slightly better for Black.
18...Nxe4! 19 Bxe4 Rxc4 20 Bxb7 Rb8 21 Bd5 Bf5+ 22 Ka1 Rc2
Now White suddenly realised that the intended 23 Bb3 fails to 23...Rxb3! 24 axb3 Rc6! and there is no way to stop Ra6 mate. The only chance to resist was 23 Rb1...`,
    preparsedJson: {
      game_id: "game_1_trap",
      white: "Book Analyzer",
      black: "The Tactician",
      event: "Tactical Demonstration",
      initial_moves: "1 e4 d6 2 d4 Nf6 3 Nc3 g6 4 Nf3 Bg7 5 Be2 O-O 6 O-O c6 7 a4 Nbd7 8 h3 e5 9 dxe5 dxe5 10 Qd6 Re8 11 Bc4 Bf8 12 Qd3 h6 13 Be3 Qe7 14 Rfd1",
      interactive_section: {
        starting_move: 14,
        moves: [
          {
            move_number: 14,
            player: "B",
            move: "Nc5",
            commentary: "Black targets the White queen on d3, beginning active piece maneuvering."
          },
          {
            move_number: 15,
            player: "W",
            move: "Nc4?!",
            commentary: "A slight mistake and inaccurate. Allows Black tactical tricks based on ...Nxe4, while the knight may also get booted by ...b7-b5 later."
          },
          {
            move_number: 15,
            player: "B",
            move: "Bf8",
            commentary: "Prophylactic. Keeps the white knight out of the d6 hole, and transitions the dark-square bishop to of more active, defensive file."
          },
          {
            move_number: 16,
            player: "W",
            move: "O-O-O",
            commentary: "On the last move castling queenside was best, but now it is rather risky."
          },
          {
            move_number: 16,
            player: "B",
            move: "Be6",
            commentary: "Developing the light-square bishop with tempo, attacking the c4 knight."
          },
          {
            move_number: 17,
            player: "W",
            move: "Kb1",
            commentary: "Slipping the King to safety on the b1 square."
          },
          {
            move_number: 17,
            player: "B",
            move: "Rac8",
            commentary: "Black wants more. Preparing to launch a hidden tactic instead of playing the simple 17...Nxe4."
          },
          {
            move_number: 18,
            player: "W",
            move: "Be3?",
            commentary: "Thank you very much! White falls completely for the trap. Better was 18 Rhe1."
          },
          {
            move_number: 18,
            player: "B",
            move: "Nxe4!",
            commentary: "Ka-boom! Black executes the tactical blow, sacrificing piece coordination for a mating visual."
          },
          {
            move_number: 19,
            player: "W",
            move: "Bxe4",
            commentary: "White captures the knight, hoping for safety."
          },
          {
            move_number: 19,
            player: "B",
            move: "Rxc4",
            commentary: "Recapturing with the rook, now bearing down on the white king."
          },
          {
            move_number: 20,
            player: "W",
            move: "Bxb7",
            commentary: "Desperately capturing a pawn on b7."
          },
          {
            move_number: 20,
            player: "B",
            move: "Rb8",
            commentary: "Targeting the bishop on the b-file, gaining more storming tempo."
          },
          {
            move_number: 21,
            player: "W",
            move: "Bd5",
            commentary: "Failing to see the danger, White occupies d5."
          },
          {
            move_number: 21,
            player: "B",
            move: "Bf5+",
            commentary: "Check! The light-square bishop joins the assault with maximum brutality."
          },
          {
            move_number: 22,
            player: "W",
            move: "Ka1",
            commentary: "King slips away into the corner."
          },
          {
            move_number: 22,
            player: "B",
            move: "Rc2",
            commentary: "Infiltration! Now White realizes that his intended 23 Bb3 fails to 23...Rxb3! 24 axb3 Rc6! and nothing stops Ra6 mate!"
          },
          {
            move_number: 23,
            player: "W",
            move: "Bxa7?",
            commentary: "A final blunder, grabbing a useless b7 pawn."
          },
          {
            move_number: 23,
            player: "B",
            move: "Rbxb2",
            commentary: "Rooks have completely dominated the second rank."
          },
          {
            move_number: 24,
            player: "W",
            move: "Be3",
            commentary: "Desperate defense of the back rank."
          },
          {
            move_number: 24,
            player: "B",
            move: "Bb4",
            commentary: "Setting up a final mating blow."
          },
          {
            move_number: 25,
            player: "W",
            move: "g4",
            commentary: "Kicking the bishop, but it is too late."
          },
          {
            move_number: 25,
            player: "B",
            move: "Bc3!",
            commentary: "A beautiful checkmate visual on Diagram 6! White resigns."
          }
        ]
      },
      sidelines: [
        {
          id: "game_1_best_15",
          name: "Verify 15. O-O-O! (Best)",
          description: "Author's advice: White should castle immediately, neutralizing Black's aggressive plans.",
          startingMoveIndex: 0, // Starts after 14...Nc5 (index 0)
          moves: [
            {
              move_number: 15,
              player: "W",
              move: "O-O-O",
              commentary: "White castles queenside! The king seeks shelter, and the rook takes control of the d-file, neutralising any immediate threats."
            },
            {
              move_number: 15,
              player: "B",
              move: "Ne6!",
              commentary: "Black transfers the knight to a defensive, centralized anchor on e6. The author notes this leads to complete equality."
            }
          ]
        },
        {
          id: "game_1_blunder_15",
          name: "Explore 15...Nd3+? blunder",
          description: "See why the impetuous knight jump looks scary but actually fails.",
          startingMoveIndex: 0, // Starts after 14...Nc5
          moves: [
            {
              move_number: 15,
              player: "W",
              move: "O-O-O",
              commentary: "First castling as recommended."
            },
            {
              move_number: 15,
              player: "B",
              move: "Nd3+",
              commentary: "Black tries to play the aggressive Nd3+ check immediately."
            },
            {
              move_number: 16,
              player: "W",
              move: "Kb1",
              commentary: "Slipping the white King to b1. Black lacks proper coordination to sustain the pieces, leaving the knight on d3 overextended and lost."
            }
          ]
        },
        {
          id: "game_1_alt_18",
          name: "Defend with 18. Rhe1",
          description: "White escapes the trap by reinforcing the critical e4 square.",
          startingMoveIndex: 6, // Starts after 17...Rac8 (index 6)
          moves: [
            {
              move_number: 18,
              player: "W",
              move: "Rhe1",
              commentary: "Shoring up the center and protecting the f1 and e4 corridors before any knight sacrifices."
            },
            {
              move_number: 18,
              player: "B",
              move: "Bxd5",
              commentary: "Black takes on d5 to resolve space tensions."
            },
            {
              move_number: 19,
              player: "W",
              move: "exd5",
              commentary: "Recaptured. The commentary notes Black is slightly better here, but White has avoided the deadly mate on c2!"
            }
          ]
        }
      ]
    }
  }
];
