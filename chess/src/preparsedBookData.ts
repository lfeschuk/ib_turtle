import { SampleBookPage } from './types';

export const COMPLED_EXERCISES: SampleBookPage[] = [
  {
    id: "exc_1",
    title: "Exercise 1: Avoid the Knight Bait",
    description: "Chapter 1 (Alternatives to 7 O-O) - Page 14. Testing the tactical consequences of White trying to snitch a centralized pawn with 9. Nxe5?",
    imageFilename: "chess_board.png",
    textContext: "Exercise 1: You may have spotted 9 Nxe5?. How does Black respond?",
    preparsedJson: {
      game_id: "exercise_1",
      white: "Gallagher-Book-Trap",
      black: "Chess Codex Solver",
      event: "Exercise 1, Page 14",
      initial_moves: "d4 Nf6 c4 g6 Nc3 Bg7 e4 d6 Nf3 O-O Be2 e5 dxe5 dxe5 Qxd8 Rxd8 Bg5 Re8",
      interactive_section: {
        starting_move: 9,
        moves: [
          {
            move_number: 9,
            player: "W",
            move: "Nxe5?",
            commentary: "White thinks they can exploit the pin on the d-file to grab a free central pawn. Can you find the immediate tactical strike for Black to overturn the pressure?"
          },
          {
            move_number: 9,
            player: "B",
            move: "Nxe4!",
            commentary: "Sublime! Black plays 9...Nxe4!, exploiting the fact that White's e5 knight is now hanging. If 10 Nxe4, then 10...Bxe5."
          },
          {
            move_number: 10,
            player: "W",
            move: "Nxe4",
            commentary: "White trades back knights on e4. Now Black reclaims their minor piece."
          },
          {
            move_number: 10,
            player: "B",
            move: "Bxe5",
            commentary: "Perfect! Black recaptures, emerging with active central bishops and the superior double-bishop endgame, while White's bishop on g5 remains misplaced."
          }
        ]
      }
    }
  },
  {
    id: "exc_2",
    title: "Exercise 2: Breaking the Pawn Cover",
    description: "Chapter 5 (The Sämisch Variation) - Page 56. Spotting the devastating tactical rook sacrifice to shatter White's king castled pawn ring.",
    imageFilename: "chess_board.png",
    textContext: "Exercise 2: What would have happened to White if he had played 26 a7?",
    preparsedJson: {
      game_id: "exercise_2",
      white: "Gallagher-Book-Puzzles",
      black: "Chess Codex Solver",
      event: "Exercise 2, Page 56",
      initial_moves: "d4 Nf6 c4 g6 Nc3 Bg7 e4 d6 f3 O-O Be3 e5 Nge2 c6 Qd2 Nbd7 Rd1 a6 dxe5 dxe5 Nc1 Nh5 g3 Qe7",
      interactive_section: {
        starting_move: 26,
        moves: [
          {
            move_number: 26,
            player: "W",
            move: "a7?",
            commentary: "White greedily pushes the a-pawn to secure space, but totally ignores the storm gathering around their king on the h-file! Find Black's winning sequence."
          },
          {
            move_number: 26,
            player: "B",
            move: "Rxh2+!",
            commentary: "Boom! An outstanding rook sacrifice on h2! Black tears open White's defensive shelter. White must accept the rook or face instant mate."
          },
          {
            move_number: 27,
            player: "W",
            move: "Bxh2",
            commentary: "White recaptures with the bishop. How does Black bring the queen into the action?"
          },
          {
            move_number: 27,
            player: "B",
            move: "Qh7",
            commentary: "Excellent! Threatening a crushing checkmate on h1 or h2. If 28 fxg4, Black coordinates with ...Bf6-Bh4 to quickly checkmate the white king. A stunning mating net."
          }
        ]
      }
    }
  },
  {
    id: "exc_3",
    title: "Exercise 3: The King's Indian Masterpiece",
    description: "Chapter 4 (Alternatives to 9 Ne1) - Page 59. The legendary Queen sacrifice to unlock an unstoppable mating threat on the light squares.",
    imageFilename: "chess_board.png",
    textContext: "Exercise 3: White defends his position with 18 Bg1. What should Black play? Very difficult, but this contains a key idea.",
    preparsedJson: {
      game_id: "exercise_3",
      white: "Gallagher-Book-Classics",
      black: "Chess Codex Solver",
      event: "Exercise 3, Page 59",
      initial_moves: "d4 Nf6 c4 g6 Nc3 Bg7 e4 d6 Nf3 O-O Be2 e5 O-O Nc6 d5 Ne7 Nd2 a5 a3 Nd7 Rb1 f5 b4 Kh8 f3 Ng8 c5 dxc5 bxc5 Nxc5 Nc4 b6 Be3 Bd7",
      interactive_section: {
        starting_move: 18,
        moves: [
          {
            move_number: 18,
            player: "W",
            move: "Bf2",
            commentary: "White plays 18. Bf2, hoping to solidify their structure. Can you find the brilliant queen sacrifice that tears White's king's camp to shreds?"
          },
          {
            move_number: 18,
            player: "B",
            move: "Qh4!!",
            commentary: "Stunning! A legendary queen sacrifice. This vacates the h5-square for the black knight and prepares a devastating checkmate thread. White is helpless!"
          },
          {
            move_number: 19,
            player: "W",
            move: "Nxc7",
            commentary: "White jumps blockading, but the black knight enters the fray with maximum pressure."
          },
          {
            move_number: 19,
            player: "B",
            move: "Nh5!",
            commentary: "The threat is ...Ng3 mate! Use the sidelines panel on the right to test White's defense attempts (like 20. Bf2 or 20. g3) and see the beautiful checkmates!"
          }
        ]
      },
      sidelines: [
        {
          id: "exc3_side_1",
          name: "Verify 20. Bf2 (Mating Theme)",
          description: "See the absolute tactical culmination of the queen sacrifice after 20. Bf2",
          startingMoveIndex: 3, // After 19...Nh5!
          moves: [
            {
              move_number: 20,
              player: "W",
              move: "Bf2",
              commentary: "White tries to cover g3 by attacking the black queen."
            },
            {
              move_number: 20,
              player: "B",
              move: "Qxh2+!!",
              commentary: "Double Exclamation! A second beautiful piece sacrifice. The queen forces the king to step out."
            },
            {
              move_number: 21,
              player: "W",
              move: "Kxh2",
              commentary: "Forced."
            },
            {
              move_number: 21,
              player: "B",
              move: "Ng3+",
              commentary: "Double check! The e4 knight opens the rook's diagonal."
            },
            {
              move_number: 22,
              player: "W",
              move: "Kg1",
              commentary: "White's only legal square."
            },
            {
              move_number: 22,
              player: "B",
              move: "Rh1#",
              commentary: "Checkmate! An immortal light-square chess miniature."
            }
          ]
        },
        {
          id: "exc3_side_2",
          name: "Verify 20. g3 (Forced Double Check)",
          description: "White plays 20. g3 to prevent the immediate knight landing.",
          startingMoveIndex: 3,
          moves: [
            {
              move_number: 20,
              player: "W",
              move: "g3",
              commentary: "Solidifying the g3 square. How does Black break through?"
            },
            {
              move_number: 20,
              player: "B",
              move: "Nxg3+",
              commentary: "Black lands the knight on g3 anyway, double-checking the White king!"
            },
            {
              move_number: 21,
              player: "W",
              move: "Kg2",
              commentary: "White's king steps up."
            },
            {
              move_number: 21,
              player: "B",
              move: "Bh3+",
              commentary: "Check! Light bishops and knights coordinating dynamically."
            },
            {
              move_number: 22,
              player: "W",
              move: "Kf2",
              commentary: "Step back."
            },
            {
              move_number: 22,
              player: "B",
              move: "Nh1#",
              commentary: "Mated! Beautiful double checkmate by the knights and bishop!"
            }
          ]
        }
      ]
    }
  },
  {
    id: "exc_4",
    title: "Exercise 4: The Royal Fork Trap",
    description: "Chapter 4 (The Bayonet 9 b4) - Page 64. A critical lesson on avoiding positional capture bait that drops into a devastating Queen loss.",
    imageFilename: "chess_board.png",
    textContext: "Exercise 4: Why didn't Black play 17...Qxe6?",
    preparsedJson: {
      game_id: "exercise_4",
      white: "Gallagher-Book-Tactics",
      black: "Chess Codex Solver",
      event: "Exercise 4, Page 64",
      initial_moves: "d4 Nf6 c4 g6 Nc3 Bg7 e4 d6 Nf3 O-O Be2 e5 O-O Nc6 d5 Ne7 Nd2 c5 a3 Ne8 b4 b6 Rb1 f5 f3 f4 a4 g5 a5 Rf6 axb6 axb6 Rb1",
      interactive_section: {
        starting_move: 17,
        moves: [
          {
            move_number: 17,
            player: "W",
            move: "Re1",
            commentary: "White shifts a rook. 17...Qxe6 looks like a free, powerful central capture. Why is it an absolute blunder for Black?"
          },
          {
            move_number: 17,
            player: "B",
            move: "Qxe6",
            commentary: "Let's perform the greedy caption to see how White instantly punishes this blunder."
          },
          {
            move_number: 18,
            player: "W",
            move: "Rxd6!",
            commentary: "Whack! White strikes with 18. Rxd6!, double-attacking Black's central pieces. If Black captures 18...Qxd6, can you find the follow-up?"
          },
          {
            move_number: 18,
            player: "B",
            move: "Qxd6",
            commentary: "Black takes the rook on d6, but..."
          },
          {
            move_number: 19,
            player: "W",
            move: "c5+",
            commentary: "Bang! The royal bishop/queen fork with 19. c5+ checks the Black king and wins the black queen on the next move. An invaluable structural tactic!"
          }
        ]
      }
    }
  },
  {
    id: "exc_5",
    title: "Exercise 5: Sämisch Central Counter",
    description: "Chapter 5 (The Sämisch Variation) - Page 99. Demonstrating the classic ...Nxe4 and ...Qh4+ sequence to shatter early White greed.",
    imageFilename: "chess_board.png",
    textContext: "Exercise 5: Why didn't White play 11 Bxh6?",
    preparsedJson: {
      game_id: "exercise_5",
      white: "Gallagher-Book-Sämisch",
      black: "Chess Codex Solver",
      event: "Exercise 5, Page 99",
      initial_moves: "d4 Nf6 c4 g6 Nc3 Bg7 e4 d6 f3 O-O Be3 e5 Nge2 c5 d5 e6 Qd2 exd5 cxd5 a6 a4 h6",
      interactive_section: {
        starting_move: 11,
        moves: [
          {
            move_number: 11,
            player: "W",
            move: "Bxh6",
            commentary: "White plays 11. Bxh6. This looks like a solid trade, but it allows Black to blow open the center using an key KID tactic! Find the blow."
          },
          {
            move_number: 11,
            player: "B",
            move: "Nxe4!",
            commentary: "Sensational! Black plays 11...Nxe4!, exploiting the undefended state of White's center and starting a double-attack. If 12 fxe4, Qh4+ forks king and bishop."
          },
          {
            move_number: 12,
            player: "W",
            move: "Nxe4",
            commentary: "White trades back knights. How does Black execute the fork?"
          },
          {
            move_number: 12,
            player: "B",
            move: "Qh4+",
            commentary: "Bingo! 12...Qh4+ checks the king on e1 and wins the h6 bishop on the next move, leaving Black with a magnificent center, better development, and extra material."
          }
        ]
      }
    }
  },
  {
    id: "exc_6",
    title: "Exercise 6: The Overloaded Recapture",
    description: "Chapter 5 (The Sämisch Variation) - Page 100. Spotting the visual overload sequence on the e3/h6 light square sector.",
    imageFilename: "chess_board.png",
    textContext: "Exercise 6: What does Black have in mind after 13 Bxh6?",
    preparsedJson: {
      game_id: "exercise_6",
      white: "Gallagher-Book-Study",
      black: "Chess Codex Solver",
      event: "Exercise 6, Page 100",
      initial_moves: "d4 Nf6 c4 g6 Nc3 Bg7 e4 d6 f3 O-O Be3 e5 Nge2 c5 d5 e6 Qd2 exd5 cxd5 a6 a4 h6 Bxh6 Nxe4 Nxe4",
      interactive_section: {
        starting_move: 13,
        moves: [
          {
            move_number: 13,
            player: "W",
            move: "Bxh6",
            commentary: "White proceeds with 13. Bxh6, thinking they can gain the initiative. Show them why this is a fatal blunder."
          },
          {
            move_number: 13,
            player: "B",
            move: "Qh4+!",
            commentary: "Boom! The immediate royal fork on h4. The queen checks White's king and collects the newly-arrived h6 bishop, winning valuable initiative."
          }
        ]
      }
    }
  },
  {
    id: "exc_7",
    title: "Exercise 7: Fianchetto Center Cleomp",
    description: "Chapter 6 (The Fianchetto Variation) - Page 111. Overloading White's center protectors using a subtle tactical exchange on e4.",
    imageFilename: "chess_board.png",
    textContext: "Exercise 7: What does Black play now?",
    preparsedJson: {
      game_id: "exercise_7",
      white: "Gallagher-Book-Fianchetto",
      black: "Chess Codex Solver",
      event: "Exercise 7, Page 111",
      initial_moves: "d4 Nf6 c4 g6 Nf3 Bg7 g3 O-O Bg2 d6 Nc3 Nbd7 O-O e5 e4 c6 h3 Qb6 Re1 exd4 Nxd4 Re8",
      interactive_section: {
        starting_move: 15,
        moves: [
          {
            move_number: 15,
            player: "W",
            move: "Be3",
            commentary: "White defends with 15. Be3. Black has a fabulous opportunity to exploit the overloaded state of White's center. Can you find it?"
          },
          {
            move_number: 15,
            player: "B",
            move: "Nxe4!",
            commentary: "Spot on! 15...Nxe4!. This brilliant strike exploits White's loose knights on f3/c3. If White takes on e4, Black captures the d4 prize."
          },
          {
            move_number: 16,
            player: "W",
            move: "Nxe4",
            commentary: "White trades back. Now Black reclaims material with a powerful pawn capture."
          },
          {
            move_number: 16,
            player: "B",
            move: "Qxd4",
            commentary: "Excellent! Black pockets the central pawn and keeps an incredibly active, superior chess position."
          }
        ]
      }
    }
  },
  {
    id: "exc_8",
    title: "Exercise 8: Punish Passive Defense",
    description: "Chapter 7 (The Four Pawns Attack) - Page 135. Spotting the pin exploit sequence to dismantle White's overextended pawn wall.",
    imageFilename: "chess_board.png",
    textContext: "Exercise 8: After 9...Nc5 what happens if White defends the pawn with 10 Qc2?",
    preparsedJson: {
      game_id: "exercise_8",
      white: "Gallagher-Four-Pawns",
      black: "Chess Codex Solver",
      event: "Exercise 8, Page 135",
      initial_moves: "d4 Nf6 c4 g6 Nc3 Bg7 e4 d6 f4 O-O Nf3 c5 d5 e6 Be2 exd5 cxd5 Re8",
      interactive_section: {
        starting_move: 9,
        moves: [
          {
            move_number: 9,
            player: "B",
            move: "Nc5",
            commentary: "Black develops the knight to c5, targeting the e4 pawn. White responds with a passive queen move..."
          },
          {
            move_number: 10,
            player: "W",
            move: "Qc2?",
            commentary: "White tries to defend with the queen, but this falls into a devastating tactical sequence! Find the strike."
          },
          {
            move_number: 10,
            player: "B",
            move: "Nfxe4!",
            commentary: "Fantastic! Black strikes on e4 anyway. After White captures back, Black plays the pinning bishop strike."
          },
          {
            move_number: 11,
            player: "W",
            move: "Nxe4",
            commentary: "White trades. How does Black exploit the pin?"
          },
          {
            move_number: 11,
            player: "B",
            move: "Bf5",
            commentary: "Incredibly strong! Black pins the e4 knight against the queen on c2. The overload on the e-file wins a complete minor piece for Black."
          }
        ]
      }
    }
  },
  {
    id: "exc_9",
    title: "Exercise 9: Exploding the Averbakh Bishop",
    description: "Chapter 8 (The Averbakh Variation) - Page 146. A beautiful test demonstrating tactics on the g5/e4 light squares.",
    imageFilename: "chess_board.png",
    textContext: "Exercise 9: Where does the knight go after 11 b4?",
    preparsedJson: {
      game_id: "exercise_9",
      white: "Gallagher-Averbakh",
      black: "Chess Codex Solver",
      event: "Exercise 9, Page 146",
      initial_moves: "d4 Nf6 c4 g6 Nc3 Bg7 e4 d6 Be2 O-O Bg5 c5 d5 e6 Qd2 exd5 exd5 Re8 Nf3 Bf5 O-O Nbd7 Rae1",
      interactive_section: {
        starting_move: 11,
        moves: [
          {
            move_number: 11,
            player: "W",
            move: "b4?",
            commentary: "White plays 11. b4? to kick Black's pieces, but this ignores a classical KID tactic. Find the counter-blow!"
          },
          {
            move_number: 11,
            player: "B",
            move: "Nxe4!",
            commentary: "Exactly! Black plays the magnificent ...Nxe4!, exploiting the overloaded white defenders. If 12 Nxe4, Black collects White's loose queen on d2."
          },
          {
            move_number: 12,
            player: "W",
            move: "Nxe4",
            commentary: "Trade. Now Black collects the queen."
          },
          {
            move_number: 12,
            player: "B",
            move: "Bxe4",
            commentary: "Perfect! Black trades pieces, completely dismantling White's center and winning a solid pawn."
          }
        ]
      }
    }
  },
  {
    id: "exc_10",
    title: "Exercise 10: Positional Masterstroke",
    description: "Chapter 9 (White Plays h2-h3) - Page 160. Learning a beautiful grandmaster positional maneuver to recycle an offside knight.",
    imageFilename: "chess_board.png",
    textContext: "Exercise 10: What should Black play now?",
    preparsedJson: {
      game_id: "exercise_10",
      white: "Gallagher-h2-h3-Chapter",
      black: "Chess Codex Solver",
      event: "Exercise 10, Page 160",
      initial_moves: "d4 Nf6 c4 g6 Nc3 Bg7 e4 d6 h3 O-O Bg5 Na6 Nf3 e5 d5 Qe8 Be2 Nh5 Qd2 f5",
      interactive_section: {
        starting_move: 24,
        moves: [
          {
            move_number: 24,
            player: "W",
            move: "a3",
            commentary: "White plays a defensive a3 move. Black's knight on a6 is currently passive and cut off. Can you find a famous positional rerouting maneuver?"
          },
          {
            move_number: 24,
            player: "B",
            move: "Nb8!",
            commentary: "Masterclass! Instead of attacking blindly, Black plays 24...Nb8!. This excellent recycling allows the knight to march back into the game via d7-f6 to dominate."
          }
        ]
      }
    }
  },
  {
    id: "exc_11",
    title: "Exercise 11: The Mating Guard on h7",
    description: "Chapter 10 (Other Systems) - Page 173. A vital structural warning on avoiding a common trap that fails due to deep mate on h7.",
    imageFilename: "chess_board.png",
    textContext: "Exercise 11: Black would like to play 11...g5 12 Bg3 Nh5 but the author notes this loses. Why?",
    preparsedJson: {
      game_id: "exercise_11",
      white: "Gallagher-Other-Systems",
      black: "Chess Codex Solver",
      event: "Exercise 11, Page 173",
      initial_moves: "d4 Nf6 c4 g6 Nc3 Bg7 e4 d6 Be3 O-O Be2 e5 d5 a5 Nf3 Na6 Nd2 Nd7 O-O",
      interactive_section: {
        starting_move: 11,
        moves: [
          {
            move_number: 11,
            player: "B",
            move: "g5",
            commentary: "Let's test the risky 11...g5 to understand why it falls apart."
          },
          {
            move_number: 12,
            player: "W",
            move: "Bg3",
            commentary: "White retreats the bishop. Now Black thinks they can grab it with ...Nh5."
          },
          {
            move_number: 12,
            player: "B",
            move: "Nh5?",
            commentary: "Black plays 12...Nh5? expecting standard options, but White has a deadly response!"
          },
          {
            move_number: 13,
            player: "W",
            move: "Nxg5!",
            commentary: "Boom! White strikes with 13. Nxg5!. Black cannot capture back recapturing on g3 because White's queen is now threatening a swift, unstoppable checkmate on h7!"
          }
        ]
      }
    }
  }
];

export const STATIC_ILLUSTRATIVE_GAMES: SampleBookPage[] = [
  {
    id: "game_3",
    title: "Game 3: Lyrberg vs Bologan (Oslo 1994)",
    description: "Chapter 1 (The Petrosian System) - Page 18. A glorious display of the Petrosian variation, showcasing Black's pawn storms on the kingside to overwhelm White.",
    imageFilename: "chess_board.png",
    textContext: "Game 3: Lyrberg vs Bologan, Oslo 1994. 1 Nf3 Nf6 2 c4 g6 3 Nc3 Bg7 4 e4 d6 5 d4 O-O 6 Be2 e5 7 d5 Nbd7",
    preparsedJson: {
      game_id: "game_3",
      white: "Lyrberg",
      black: "Bologan",
      event: "Oslo 1994",
      initial_moves: "d4 Nf6 c4 g6 Nc3 Bg7 e4 d6 Nf3 O-O Be2 e5 d5 a5 Bg5 h6 Bh4 Na6 Nd2 Qe8",
      interactive_section: {
        starting_move: 11,
        moves: [
          {
            move_number: 11,
            player: "W",
            move: "h4!",
            commentary: "A sharp, aggressive thrust! White commits to locking Black's options on the kingside before committing the King."
          },
          {
            move_number: 11,
            player: "B",
            move: "Nxg3",
            commentary: "Black immediately jumps on the opportunity, trading the knight for the active bishop."
          },
          {
            move_number: 12,
            player: "W",
            move: "fxg3",
            commentary: "Recaptured. The open f-pawn gives White a solid center but opens up visual counter-opportunities for Black."
          },
          {
            move_number: 12,
            player: "B",
            move: "g4",
            commentary: "Aggressive pawn charge! Black stakes direct claims, seeking space on the kingside."
          },
          {
            move_number: 13,
            player: "W",
            move: "Nh2",
            commentary: "White retreats the knight defensively."
          },
          {
            move_number: 13,
            player: "B",
            move: "h5",
            commentary: "Black continues the storm, locking down the light squares on the h-file."
          }
        ]
      }
    }
  },
  {
    id: "game_28",
    title: "Game 28: Ljubojevic vs Kasparov (Linares 1993)",
    description: "Chapter 4 (The Classical variation) - Page 77. The legendary encounter showing Garry Kasparov's immortal kingside pawn storm to force a magnificent victory against Lubomir Ljubojevic.",
    imageFilename: "chess_board.png",
    textContext: "Game 28: Ljubojevic vs Kasparov, Linares 1993. 1 d4 Nf6 2 c4 g6 3 Nc3 Bg7 4 e4 d6 5 Nf3 O-O",
    preparsedJson: {
      game_id: "game_28",
      white: "Ljubojevic",
      black: "Kasparov",
      event: "Linares 1993",
      initial_moves: "d4 Nf6 c4 g6 Nc3 Bg7 e4 d6 Nf3 O-O Be2 e5 O-O Nc6 d5 Ne7 Ne1 Nd7 Nd3 f5 Bd2 Nf6 f3 f4 c5 g5 Rc1 Ng6 cxd6 cxd6 Nb5 Rf7 Qc2 Ne8 a4 h5 Nf2 Bf8 a5 Bd7 Qb3 Rg7 h3 Nh4 Rc3 a6 Na3",
      interactive_section: {
        starting_move: 24,
        moves: [
          {
            move_number: 24,
            player: "W",
            move: "g4!",
            commentary: "White tries to preemptively lock down the kingside with g4, trying to halt Black's storm."
          },
          {
            move_number: 24,
            player: "B",
            move: "hxg4",
            commentary: "Kasparov immediately trades, opening up the f-file for the rooks."
          },
          {
            move_number: 25,
            player: "W",
            move: "fxg4",
            commentary: "Recaptured. The lines are open!"
          },
          {
            move_number: 25,
            player: "B",
            move: "b5!",
            commentary: "A beautiful queenside response! Challenging White's structural alignment and creating dynamic counter-thrusts."
          }
        ]
      }
    }
  }
];
