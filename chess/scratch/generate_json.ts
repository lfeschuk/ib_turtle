import * as fs from 'fs';

interface Move {
  move_number: number;
  player: string;
  move: string;
  commentary?: string;
}

interface Sideline {
  id: string;
  name: string;
  description?: string;
  startingMoveIndex: number;
  moves: Move[];
}

interface Exercise {
  id: string;
  title: string;
  description: string;
  textContext: string;
  preparsedJson: {
    game_id: string;
    white: string;
    black: string;
    event?: string;
    initial_moves: string;
    interactive_section: {
      starting_move: number;
      moves: Move[];
    };
    sidelines?: Sideline[];
  };
}

interface ParsedFile {
  book_title: string;
  exercises: Exercise[];
}

const file: ParsedFile = {
  book_title: "Starting Out: The King's Indian",
  exercises: [
    {
      id: "game_46_arkell_buckley",
      title: "Game 46: Arkell vs. Buckley (South Wales Masters 2001)",
      description: "Digitized from PDF chunk parsed_pages_121_125.json",
      textContext: "Extracted from Starting Out: The King's Indian.",
      preparsedJson: {
        game_id: "game_46_arkell_buckley",
        white: "Arkell",
        black: "Buckley",
        event: "South Wales Masters 2001",
        initial_moves: "1 d4 Nf6 2 c4 g6 3 Nf3 Bg7 4 g3 O-O 5 Bg2 d6 6 O-O Nc6 7 Nc3 a6 8 h3 Rb8 9 e4 b5 10 e5 Nd7 11 cxb5 axb5 12 Ng5",
        interactive_section: {
          starting_move: 12,
          moves: [
            {
              move_number: 12,
              player: "B",
              move: "dxe5",
              commentary: "White now has two threats. The first is to take the bishop on c6 and the other is to play 13 e6. Black has no choice but to sacrifice a piece for White's centre pawns. There are several ways to do this."
            },
            {
              move_number: 13,
              player: "W",
              move: "Bxc6",
              commentary: ""
            },
            {
              move_number: 13,
              player: "B",
              move: "exd4",
              commentary: ""
            },
            {
              move_number: 14,
              player: "W",
              move: "Nxb5",
              commentary: ""
            },
            {
              move_number: 14,
              player: "B",
              move: "Rb6",
              commentary: "Diagram 20: White is a piece for a pawn up but in a bit of a tangle. If the bishop retreats Black just takes the knight so let's have a look at his other attempts to save the piece."
            },
            {
              move_number: 15,
              player: "W",
              move: "Nxd4!",
              commentary: ""
            },
            {
              move_number: 15,
              player: "B",
              move: "Nb8!",
              commentary: "Now White has two pieces attacked and must lose one of them."
            },
            {
              move_number: 16,
              player: "W",
              move: "Nde6!",
              commentary: ""
            },
            {
              move_number: 16,
              player: "B",
              move: "Qxd1",
              commentary: ""
            },
            {
              move_number: 17,
              player: "W",
              move: "Rxd1",
              commentary: ""
            },
            {
              move_number: 17,
              player: "B",
              move: "Bxe6",
              commentary: ""
            },
            {
              move_number: 18,
              player: "W",
              move: "Nxe6",
              commentary: ""
            },
            {
              move_number: 18,
              player: "B",
              move: "fxe6",
              commentary: ""
            },
            {
              move_number: 19,
              player: "W",
              move: "Be4!",
              commentary: "The first new move but it wouldn't surprise me if Arkell had already played this in previous unpublished games."
            },
            {
              move_number: 19,
              player: "B",
              move: "Bxb2",
              commentary: ""
            },
            {
              move_number: 20,
              player: "W",
              move: "Rb1",
              commentary: ""
            },
            {
              move_number: 20,
              player: "B",
              move: "Bxc1",
              commentary: ""
            },
            {
              move_number: 21,
              player: "W",
              move: "Rbxc1",
              commentary: "Diagram 21: The difference with the game above is that Black can no longer play 20...Bd4 as the white rook on b1 is defended. White now has a clear advantage in the endgame. The remaining moves were:"
            },
            {
              move_number: 21,
              player: "B",
              move: "Na6",
              commentary: ""
            },
            {
              move_number: 22,
              player: "W",
              move: "Rd2",
              commentary: ""
            },
            {
              move_number: 22,
              player: "B",
              move: "Rfb8",
              commentary: ""
            },
            {
              move_number: 23,
              player: "W",
              move: "Kf1",
              commentary: ""
            },
            {
              move_number: 23,
              player: "B",
              move: "Rd6",
              commentary: ""
            },
            {
              move_number: 24,
              player: "W",
              move: "Re2",
              commentary: ""
            },
            {
              move_number: 24,
              player: "B",
              move: "c5",
              commentary: ""
            },
            {
              move_number: 25,
              player: "W",
              move: "Rc3",
              commentary: ""
            },
            {
              move_number: 25,
              player: "B",
              move: "Rbb6",
              commentary: ""
            },
            {
              move_number: 26,
              player: "W",
              move: "Bd3",
              commentary: ""
            },
            {
              move_number: 26,
              player: "B",
              move: "Nb4",
              commentary: ""
            },
            {
              move_number: 27,
              player: "W",
              move: "Bc4",
              commentary: ""
            },
            {
              move_number: 27,
              player: "B",
              move: "Kf7",
              commentary: ""
            },
            {
              move_number: 28,
              player: "W",
              move: "Rce3",
              commentary: ""
            },
            {
              move_number: 28,
              player: "B",
              move: "Kf6",
              commentary: ""
            },
            {
              move_number: 29,
              player: "W",
              move: "Rf3+",
              commentary: ""
            },
            {
              move_number: 29,
              player: "B",
              move: "Kg7",
              commentary: ""
            },
            {
              move_number: 30,
              player: "W",
              move: "Rfe3",
              commentary: ""
            },
            {
              move_number: 30,
              player: "B",
              move: "Kf6",
              commentary: ""
            },
            {
              move_number: 31,
              player: "W",
              move: "a4",
              commentary: ""
            },
            {
              move_number: 31,
              player: "B",
              move: "Nd5",
              commentary: ""
            },
            {
              move_number: 32,
              player: "W",
              move: "Rf3+",
              commentary: ""
            },
            {
              move_number: 32,
              player: "B",
              move: "Kg7",
              commentary: ""
            },
            {
              move_number: 33,
              player: "W",
              move: "a5",
              commentary: ""
            },
            {
              move_number: 33,
              player: "B",
              move: "Rb7",
              commentary: ""
            },
            {
              move_number: 34,
              player: "W",
              move: "a6",
              commentary: ""
            },
            {
              move_number: 34,
              player: "B",
              move: "Ra7",
              commentary: ""
            },
            {
              move_number: 35,
              player: "W",
              move: "h4",
              commentary: ""
            },
            {
              move_number: 35,
              player: "B",
              move: "h5",
              commentary: ""
            },
            {
              move_number: 36,
              player: "W",
              move: "Re5",
              commentary: ""
            },
            {
              move_number: 36,
              player: "B",
              move: "Nb6",
              commentary: ""
            },
            {
              move_number: 37,
              player: "W",
              move: "Bxe6",
              commentary: ""
            },
            {
              move_number: 37,
              player: "B",
              move: "Rxa6",
              commentary: ""
            },
            {
              move_number: 38,
              player: "W",
              move: "Rf7+",
              commentary: ""
            },
            {
              move_number: 38,
              player: "B",
              move: "Kh6",
              commentary: ""
            },
            {
              move_number: 39,
              player: "W",
              move: "Rxe7",
              commentary: ""
            },
            {
              move_number: 39,
              player: "B",
              move: "c4",
              commentary: ""
            },
            {
              move_number: 40,
              player: "W",
              move: "Rc5",
              commentary: ""
            },
            {
              move_number: 40,
              player: "B",
              move: "Ra1+",
              commentary: ""
            },
            {
              move_number: 41,
              player: "W",
              move: "Kg2",
              commentary: ""
            },
            {
              move_number: 41,
              player: "B",
              move: "Re1",
              commentary: ""
            },
            {
              move_number: 42,
              player: "W",
              move: "Rcc7!",
              commentary: ""
            },
            {
              move_number: 42,
              player: "B",
              move: "Rd7!",
              commentary: ""
            },
            {
              move_number: 43,
              player: "W",
              move: "Rexd7",
              commentary: ""
            },
            {
              move_number: 43,
              player: "B",
              move: "Nxd7",
              commentary: ""
            },
            {
              move_number: 44,
              player: "W",
              move: "Bxd7",
              commentary: ""
            },
            {
              move_number: 44,
              player: "B",
              move: "Re7",
              commentary: ""
            },
            {
              move_number: 45,
              player: "W",
              move: "f4!",
              commentary: ""
            },
            {
              move_number: 45,
              player: "B",
              move: "c3",
              commentary: ""
            },
            {
              move_number: 46,
              player: "W",
              move: "f5!",
              commentary: ""
            },
            {
              move_number: 46,
              player: "B",
              move: "Kh7",
              commentary: ""
            },
            {
              move_number: 47,
              player: "W",
              move: "f6",
              commentary: ""
            },
            {
              move_number: 47,
              player: "B",
              move: "Rf7",
              commentary: ""
            },
            {
              move_number: 48,
              player: "W",
              move: "Kf3?",
              commentary: "White slips up. 48 Ke2! was better."
            },
            {
              move_number: 48,
              player: "B",
              move: "Rxf6+",
              commentary: ""
            },
            {
              move_number: 49,
              player: "W",
              move: "Ke2",
              commentary: ""
            },
            {
              move_number: 49,
              player: "B",
              move: "Rf7",
              commentary: ""
            },
            {
              move_number: 50,
              player: "W",
              move: "Kd1",
              commentary: ""
            },
            {
              move_number: 50,
              player: "B",
              move: "Kh6",
              commentary: ""
            },
            {
              move_number: 51,
              player: "W",
              move: "Kc2",
              commentary: ""
            },
            {
              move_number: 51,
              player: "B",
              move: "Rf3?",
              commentary: "Black returns the favour. 51...g5! was necessary."
            },
            {
              move_number: 52,
              player: "W",
              move: "Rxc3",
              commentary: ""
            },
            {
              move_number: 52,
              player: "B",
              move: "Rf7",
              commentary: ""
            },
            {
              move_number: 53,
              player: "W",
              move: "Bc8",
              commentary: ""
            },
            {
              move_number: 53,
              player: "B",
              move: "Rf6",
              commentary: ""
            },
            {
              move_number: 54,
              player: "W",
              move: "Kd2",
              commentary: ""
            },
            {
              move_number: 54,
              player: "B",
              move: "g5",
              commentary: ""
            },
            {
              move_number: 55,
              player: "W",
              move: "hxg5+",
              commentary: ""
            },
            {
              move_number: 55,
              player: "B",
              move: "Kxg5",
              commentary: ""
            },
            {
              move_number: 56,
              player: "W",
              move: "Rc5+",
              commentary: ""
            },
            {
              move_number: 56,
              player: "B",
              move: "Kg6",
              commentary: ""
            },
            {
              move_number: 57,
              player: "W",
              move: "Ke3",
              commentary: ""
            },
            {
              move_number: 57,
              player: "B",
              move: "h4",
              commentary: ""
            },
            {
              move_number: 58,
              player: "W",
              move: "g4",
              commentary: ""
            },
            {
              move_number: 58,
              player: "B",
              move: "h3",
              commentary: ""
            },
            {
              move_number: 59,
              player: "W",
              move: "Rh5",
              commentary: ""
            },
            {
              move_number: 59,
              player: "B",
              move: "Rb6",
              commentary: ""
            },
            {
              move_number: 60,
              player: "W",
              move: "Bf5+",
              commentary: ""
            },
            {
              move_number: 60,
              player: "B",
              move: "Kg7",
              commentary: ""
            },
            {
              move_number: 61,
              player: "W",
              move: "Rxh3",
              commentary: ""
            },
            {
              move_number: 61,
              player: "B",
              move: "Rb3+",
              commentary: ""
            },
            {
              move_number: 62,
              player: "W",
              move: "Bd3",
              commentary: "Black resigns."
            }
          ]
        },
        sidelines: [
          {
            id: "game_46_side_12_Nxd4",
            name: "Alternative 12...Nxd4",
            description: "Black plays 12...Nxd4 instead of 12...dxe5",
            startingMoveIndex: -1,
            moves: [
              {
                move_number: 12,
                player: "B",
                move: "Nxd4",
                commentary: "Black has only two pawns for the piece but if he can get his centre rolling White may find that he has very few good squares on which to put all his pieces. Still, the current view seems to be that White has the better chances in the endgame."
              },
              {
                move_number: 13,
                player: "W",
                move: "Qxd4",
                commentary: ""
              },
              {
                move_number: 13,
                player: "B",
                move: "Nxe5",
                commentary: ""
              },
              {
                move_number: 14,
                player: "W",
                move: "Qh4",
                commentary: ""
              },
              {
                move_number: 14,
                player: "B",
                move: "h6",
                commentary: ""
              },
              {
                move_number: 15,
                player: "W",
                move: "Nf3",
                commentary: ""
              },
              {
                move_number: 15,
                player: "B",
                move: "Nxf3+",
                commentary: ""
              },
              {
                move_number: 16,
                player: "W",
                move: "Bxf3",
                commentary: ""
              },
              {
                move_number: 16,
                player: "B",
                move: "e6",
                commentary: ""
              },
              {
                move_number: 17,
                player: "W",
                move: "Qxd8",
                commentary: ""
              },
              {
                move_number: 17,
                player: "B",
                move: "Rxd8",
                commentary: ""
              },
              {
                move_number: 18,
                player: "W",
                move: "a4!",
                commentary: ""
              }
            ]
          },
          {
            id: "game_46_side_14_Ne2",
            name: "Alternative 14 Ne2",
            description: "White plays 14 Ne2 instead of 14 Nxb5",
            startingMoveIndex: 2,
            moves: [
              {
                move_number: 14,
                player: "W",
                move: "Ne2",
                commentary: "White should steer clear of this."
              },
              {
                move_number: 14,
                player: "B",
                move: "h6",
                commentary: ""
              },
              {
                move_number: 15,
                player: "W",
                move: "Nf3",
                commentary: ""
              },
              {
                move_number: 15,
                player: "B",
                move: "e5",
                commentary: "An example of the black centre rolling."
              }
            ]
          },
          {
            id: "game_46_side_15_Qf3",
            name: "Alternative 15 Qf3",
            description: "White plays 15 Qf3 instead of 15 Nxd4!",
            startingMoveIndex: 4,
            moves: [
              {
                move_number: 15,
                player: "W",
                move: "Qf3",
                commentary: "Obviously won't do."
              },
              {
                move_number: 15,
                player: "B",
                move: "Ne5",
                commentary: ""
              }
            ]
          },
          {
            id: "game_46_side_15_Qc2",
            name: "Alternative 15 Qc2",
            description: "White plays 15 Qc2 instead of 15 Nxd4!",
            startingMoveIndex: 4,
            moves: [
              {
                move_number: 15,
                player: "W",
                move: "Qc2",
                commentary: "Also fails to do the job."
              },
              {
                move_number: 15,
                player: "B",
                move: "d3!",
                commentary: ""
              },
              {
                move_number: 16,
                player: "W",
                move: "Qc4?",
                commentary: "16 Qxd3 limits the damage."
              },
              {
                move_number: 16,
                player: "B",
                move: "Ne5",
                commentary: ""
              },
              {
                move_number: 17,
                player: "W",
                move: "Qh4",
                commentary: ""
              },
              {
                move_number: 17,
                player: "B",
                move: "h6",
                commentary: "Black calmly stops the mate threat."
              }
            ]
          },
          {
            id: "game_46_side_15_Bxd7",
            name: "Alternative 15 Bxd7",
            description: "White plays 15 Bxd7 instead of 15 Nxd4!",
            startingMoveIndex: 4,
            moves: [
              {
                move_number: 15,
                player: "W",
                move: "Bxd7",
                commentary: ""
              },
              {
                move_number: 15,
                player: "B",
                move: "Qxd7",
                commentary: ""
              },
              {
                move_number: 16,
                player: "W",
                move: "Na3",
                commentary: ""
              },
              {
                move_number: 16,
                player: "B",
                move: "h6!",
                commentary: "Black's next move will be ...Qxh3 with very strong play on the light squares."
              }
            ]
          },
          {
            id: "game_46_side_15_Na7_A",
            name: "Alternative 15 Na7 (Branch A)",
            description: "White plays 15 Na7 followed by 16 Nxc8",
            startingMoveIndex: 4,
            moves: [
              {
                move_number: 15,
                player: "W",
                move: "Na7",
                commentary: "Most of White's efforts have concentrated around this move."
              },
              {
                move_number: 15,
                player: "B",
                move: "Nb8!",
                commentary: "The white knight will not return from its foray deep into enemy territory."
              },
              {
                move_number: 16,
                player: "W",
                move: "Nxc8",
                commentary: ""
              },
              {
                move_number: 16,
                player: "B",
                move: "Rxc6",
                commentary: ""
              },
              {
                move_number: 17,
                player: "W",
                move: "Na7",
                commentary: ""
              },
              {
                move_number: 17,
                player: "B",
                move: "Rb6!",
                commentary: "It is only a matter of time before Black regains the piece with, at least, an equal game."
              }
            ]
          },
          {
            id: "game_46_side_15_Na7_B",
            name: "Alternative 15 Na7 (Branch B)",
            description: "White plays 15 Na7 followed by 16 Bg2",
            startingMoveIndex: 4,
            moves: [
              {
                move_number: 15,
                player: "W",
                move: "Na7",
                commentary: ""
              },
              {
                move_number: 15,
                player: "B",
                move: "Nb8!",
                commentary: ""
              },
              {
                move_number: 16,
                player: "W",
                move: "Bg2",
                commentary: ""
              },
              {
                move_number: 16,
                player: "B",
                move: "Bb7",
                commentary: ""
              },
              {
                move_number: 17,
                player: "W",
                move: "a4",
                commentary: ""
              },
              {
                move_number: 17,
                player: "B",
                move: "Bxg2",
                commentary: ""
              },
              {
                move_number: 18,
                player: "W",
                move: "Kxg2",
                commentary: ""
              },
              {
                move_number: 18,
                player: "B",
                move: "c6",
                commentary: "Regaining the piece."
              }
            ]
          },
          {
            id: "game_46_side_salov_kuzmin",
            name: "Salov vs. A. Kuzmin (USSR 1981)",
            description: "Alternative 19 Bg2",
            startingMoveIndex: 12,
            moves: [
              {
                move_number: 19,
                player: "W",
                move: "Bg2",
                commentary: "This game concluded in a draw."
              },
              {
                move_number: 19,
                player: "B",
                move: "Bxb2",
                commentary: ""
              },
              {
                move_number: 20,
                player: "W",
                move: "Rb1",
                commentary: ""
              },
              {
                move_number: 20,
                player: "B",
                move: "Bd4",
                commentary: ""
              },
              {
                move_number: 21,
                player: "W",
                move: "Be3",
                commentary: ""
              },
              {
                move_number: 21,
                player: "B",
                move: "Bxe3",
                commentary: ""
              },
              {
                move_number: 22,
                player: "W",
                move: "fxe3",
                commentary: ""
              },
              {
                move_number: 22,
                player: "B",
                move: "Nd7",
                commentary: ""
              },
              {
                move_number: 23,
                player: "W",
                move: "Rxb6",
                commentary: "Draw agreed."
              }
            ]
          }
        ]
      }
    },
    {
      id: "four_pawns_attack_theory",
      title: "Theory: The Four Pawns Attack (Introduction)",
      description: "Digitized from PDF chunk parsed_pages_121_125.json",
      textContext: "Extracted from Starting Out: The King's Indian.",
      preparsedJson: {
        game_id: "four_pawns_attack_theory",
        white: "Theory",
        black: "Theory",
        event: "Chapter 7 Introduction",
        initial_moves: "1 d4 Nf6 2 c4 g6 3 Nc3 Bg7 4 e4 d6",
        interactive_section: {
          starting_move: 5,
          moves: [
            {
              move_number: 5,
              player: "W",
              move: "f4",
              commentary: "The Four Pawns Attack is the most aggressive way for White to meet the King's Indian. It is a truly dangerous system for the unprepared player to face. By the fifth move White has constructed a massive centre with the simple intention of blowing Black away."
            },
            {
              move_number: 5,
              player: "B",
              move: "O-O",
              commentary: ""
            },
            {
              move_number: 6,
              player: "W",
              move: "Nf3",
              commentary: "White will hope to achieve this by advancing e4-e5 at the right moment. If you had a centre like this a hundred years ago then it was assumed that victory was only a matter of time. Since then chess has moved on and strategies have been devised for combating such centres."
            }
          ]
        },
        sidelines: [
          {
            id: "four_pawns_theory_side_e5",
            name: "Alternative 6...e5",
            description: "Black plays 6...e5 instead of the main lines",
            startingMoveIndex: 2,
            moves: [
              {
                move_number: 6,
                player: "B",
                move: "e5",
                commentary: "White's centre cannot be destroyed so easily. The point is, though, that if Black doesn't try he is likely to be heading to the showers around move 20."
              }
            ]
          },
          {
            id: "four_pawns_theory_side_Na6",
            name: "Alternative 6...Na6",
            description: "Black plays 6...Na6 instead of 6...c5",
            startingMoveIndex: 2,
            moves: [
              {
                move_number: 6,
                player: "B",
                move: "Na6",
                commentary: "Followed by ...e7-e5. This is the subject of our third sub-section."
              }
            ]
          }
        ]
      }
    },
    {
      id: "theory_6_c5_main_line",
      title: "Theory: 6...c5 Main Line (Diagram 2)",
      description: "Digitized from PDF chunk parsed_pages_121_125.json",
      textContext: "Extracted from Starting Out: The King's Indian.",
      preparsedJson: {
        game_id: "theory_6_c5_main_line",
        white: "Theory",
        black: "Theory",
        event: "6...c5 Main Line",
        initial_moves: "1 d4 Nf6 2 c4 g6 3 Nc3 Bg7 4 e4 d6 5 f4 O-O 6 Nf3",
        interactive_section: {
          starting_move: 6,
          moves: [
            {
              move_number: 6,
              player: "B",
              move: "c5",
              commentary: "Black strikes at the centre."
            },
            {
              move_number: 7,
              player: "W",
              move: "d5",
              commentary: ""
            },
            {
              move_number: 7,
              player: "B",
              move: "e6",
              commentary: ""
            },
            {
              move_number: 8,
              player: "W",
              move: "Be2",
              commentary: ""
            },
            {
              move_number: 8,
              player: "B",
              move: "exd5",
              commentary: ""
            },
            {
              move_number: 9,
              player: "W",
              move: "cxd5",
              commentary: "Diagram 2: A typical Four Pawns position. Here we shall start our coverage with Black's 9th move. He has three options. The solid 9...Bg4, the sensible but risky 9...Re8 and the wild 9...b5. They have each been allocated a game."
            }
          ]
        },
        sidelines: [
          {
            id: "theory_6_c5_side_Bg4",
            name: "9...Bg4",
            description: "The solid 9...Bg4. Black aims to exchange the bishop for the knight on f3.",
            startingMoveIndex: 5,
            moves: [
              {
                move_number: 9,
                player: "B",
                move: "Bg4",
                commentary: "The subject of Game 47."
              }
            ]
          },
          {
            id: "theory_6_c5_side_Re8",
            name: "9...Re8",
            description: "The sensible but risky 9...Re8. Threatens the e4 pawn.",
            startingMoveIndex: 5,
            moves: [
              {
                move_number: 9,
                player: "B",
                move: "Re8",
                commentary: "The subject of Game 48."
              }
            ]
          },
          {
            id: "theory_6_c5_side_b5",
            name: "9...b5",
            description: "The wild 9...b5. Black sacrifices a pawn on b5.",
            startingMoveIndex: 5,
            moves: [
              {
                move_number: 9,
                player: "B",
                move: "b5",
                commentary: "The subject of Game 49."
              }
            ]
          }
        ]
      }
    },
    {
      id: "game_47_banikas_gallagher",
      title: "Game 47: Banikas vs. Gallagher (French League 2001)",
      description: "Digitized from PDF chunk parsed_pages_121_125.json",
      textContext: "Extracted from Starting Out: The King's Indian.",
      preparsedJson: {
        game_id: "game_47_banikas_gallagher",
        white: "Banikas",
        black: "Gallagher",
        event: "French League 2001",
        initial_moves: "1 d4 Nf6 2 c4 g6 3 Nc3 Bg7 4 e4 d6 5 f4 O-O 6 Nf3 c5 7 d5 e6 8 Be2 exd5 9 cxd5",
        interactive_section: {
          starting_move: 9,
          moves: [
            {
              move_number: 9,
              player: "B",
              move: "Bg4",
              commentary: "This is Black's most solid and reliable way of meeting the main line of the Four Pawns Attack. The idea behind 9...Bg4 is to exchange the bishop for the knight on f3. Without the knight White will find it difficult to play e4-e5. There is another reason why Black should exchange a pair of minor pieces. He has less space than White and, therefore, will find it difficult to accommodate a full set of pieces. TIP: With less space it is usually a good idea to exchange pieces."
            },
            {
              move_number: 10,
              player: "W",
              move: "O-O",
              commentary: "Black's last move did not actually prevent White from playing 10 e5 - it just rendered it harmless."
            },
            {
              move_number: 10,
              player: "B",
              move: "Nbd7",
              commentary: ""
            },
            {
              move_number: 11,
              player: "W",
              move: "Re1",
              commentary: ""
            },
            {
              move_number: 11,
              player: "B",
              move: "Re8",
              commentary: ""
            },
            {
              move_number: 12,
              player: "W",
              move: "h3",
              commentary: ""
            },
            {
              move_number: 12,
              player: "B",
              move: "Bxf3",
              commentary: ""
            },
            {
              move_number: 13,
              player: "W",
              move: "Bxf3",
              commentary: "Diagram 3: The most important factor in the position is the unbalanced pawn structure. White has a 2-1 majority in the centre whilst Black has 3-2 in his favour on the queenside. Pawn majorities need to be pushed so White will be looking to play e4-e5 and Black to expand on the queenside. Normally it is an advantage to have an extra central pawn but here this is counter-balanced by the fact that it is easier for Black to advance his majority."
            },
            {
              move_number: 13,
              player: "B",
              move: "Qa5!",
              commentary: "This is the most accurate way to prepare ...b7-b5."
            },
            {
              move_number: 14,
              player: "W",
              move: "Be3",
              commentary: ""
            },
            {
              move_number: 14,
              player: "B",
              move: "b5",
              commentary: ""
            },
            {
              move_number: 15,
              player: "W",
              move: "a3",
              commentary: ""
            },
            {
              move_number: 15,
              player: "B",
              move: "Nb6!",
              commentary: ""
            },
            {
              move_number: 16,
              player: "W",
              move: "e5",
              commentary: ""
            },
            {
              move_number: 16,
              player: "B",
              move: "Nc4!",
              commentary: ""
            },
            {
              move_number: 17,
              player: "W",
              move: "exf6",
              commentary: ""
            },
            {
              move_number: 17,
              player: "B",
              move: "Nxe3",
              commentary: ""
            },
            {
              move_number: 18,
              player: "W",
              move: "Rxe3",
              commentary: ""
            },
            {
              move_number: 18,
              player: "B",
              move: "Rxe3",
              commentary: ""
            },
            {
              move_number: 19,
              player: "W",
              move: "fxg7",
              commentary: ""
            },
            {
              move_number: 19,
              player: "B",
              move: "Rae8",
              commentary: "Diagram 4: This is the position Black had in mind when he embarked on the complications with 15...Nb6. White has a slight material advantage but this is compensated for by the fact that the black rooks are extremely active and the mobility of the white bishop is restricted by the pawn on d5. The pawn on g7 is of course doomed."
            },
            {
              move_number: 20,
              player: "W",
              move: "f5",
              commentary: ""
            },
            {
              move_number: 20,
              player: "B",
              move: "b4",
              commentary: ""
            },
            {
              move_number: 21,
              player: "W",
              move: "axb4",
              commentary: ""
            },
            {
              move_number: 21,
              player: "B",
              move: "Qxb4",
              commentary: ""
            },
            {
              move_number: 22,
              player: "W",
              move: "Qd2",
              commentary: ""
            },
            {
              move_number: 22,
              player: "B",
              move: "Qh4!",
              commentary: ""
            },
            {
              move_number: 23,
              player: "W",
              move: "fxg6",
              commentary: ""
            },
            {
              move_number: 23,
              player: "B",
              move: "hxg6",
              commentary: ""
            },
            {
              move_number: 24,
              player: "W",
              move: "Rf1",
              commentary: ""
            },
            {
              move_number: 24,
              player: "B",
              move: "a6!",
              commentary: ""
            },
            {
              move_number: 25,
              player: "W",
              move: "Nd1",
              commentary: "Amazingly enough, this is the first new move of the game."
            },
            {
              move_number: 25,
              player: "B",
              move: "R3e5",
              commentary: ""
            },
            {
              move_number: 26,
              player: "W",
              move: "Nf2",
              commentary: ""
            },
            {
              move_number: 26,
              player: "B",
              move: "f5",
              commentary: ""
            },
            {
              move_number: 27,
              player: "W",
              move: "Bd1?!",
              commentary: ""
            },
            {
              move_number: 27,
              player: "B",
              move: "Kxg7",
              commentary: ""
            },
            {
              move_number: 28,
              player: "W",
              move: "Qa5?!",
              commentary: ""
            },
            {
              move_number: 28,
              player: "B",
              move: "Rxd5",
              commentary: ""
            },
            {
              move_number: 29,
              player: "W",
              move: "Bf3",
              commentary: ""
            },
            {
              move_number: 29,
              player: "B",
              move: "Rd4",
              commentary: ""
            },
            {
              move_number: 30,
              player: "W",
              move: "Qxa6",
              commentary: ""
            },
            {
              move_number: 30,
              player: "B",
              move: "Rd2",
              commentary: ""
            },
            {
              move_number: 31,
              player: "W",
              move: "Bc6??",
              commentary: "Diagram 5: White totally lost the plot over the last few moves and he caps it off with an outright blunder. 31 Qa3! still offered hope."
            },
            {
              move_number: 31,
              player: "B",
              move: "Re1!",
              commentary: "Now 32 Rxe1 Qxf2+ 33 Kh2 Qxe1 just loses a piece. Black is threatening 32...Qxf2+ anyway."
            },
            {
              move_number: 32,
              player: "W",
              move: "Qb7+",
              commentary: ""
            },
            {
              move_number: 32,
              player: "B",
              move: "Kh6",
              commentary: ""
            },
            {
              move_number: 33,
              player: "W",
              move: "Ng4+",
              commentary: ""
            },
            {
              move_number: 33,
              player: "B",
              move: "fxg4",
              commentary: ""
            },
            {
              move_number: 34,
              player: "W",
              move: "Qf7",
              commentary: ""
            },
            {
              move_number: 34,
              player: "B",
              move: "Rxf1+",
              commentary: ""
            },
            {
              move_number: 35,
              player: "W",
              move: "Qxf1",
              commentary: ""
            },
            {
              move_number: 35,
              player: "B",
              move: "Kg7!",
              commentary: "White resigns."
            }
          ]
        },
        sidelines: [
          {
            id: "game_47_side_10_e5",
            name: "Alternative 10 e5",
            description: "White plays 10 e5 instead of 10 O-O",
            startingMoveIndex: 0,
            moves: [
              {
                move_number: 10,
                player: "W",
                move: "e5",
                commentary: "This does not actually prevent Black from playing 10 e5 - it just rendered it harmless."
              },
              {
                move_number: 10,
                player: "B",
                move: "dxe5",
                commentary: ""
              },
              {
                move_number: 11,
                player: "W",
                move: "fxe5",
                commentary: ""
              },
              {
                move_number: 11,
                player: "B",
                move: "Nfd7",
                commentary: ""
              },
              {
                move_number: 12,
                player: "W",
                move: "e6",
                commentary: ""
              },
              {
                move_number: 12,
                player: "B",
                move: "Bxf3!",
                commentary: ""
              },
              {
                move_number: 13,
                player: "W",
                move: "Bxf3",
                commentary: ""
              },
              {
                move_number: 13,
                player: "B",
                move: "Ne5",
                commentary: "The position is thought to be about level."
              }
            ]
          },
          {
            id: "game_47_side_11_h3_g4",
            name: "Alternative 11 h3 & 13 g4",
            description: "White plays 11 h3 instead of 11 Re1, and then tries 13 g4",
            startingMoveIndex: 2,
            moves: [
              {
                move_number: 11,
                player: "W",
                move: "h3",
                commentary: "11 h3 Bxf3 12 Bxf3 Re8 13 Re1 just transposes."
              },
              {
                move_number: 11,
                player: "B",
                move: "Bxf3",
                commentary: ""
              },
              {
                move_number: 12,
                player: "W",
                move: "Bxf3",
                commentary: ""
              },
              {
                move_number: 12,
                player: "B",
                move: "Re8",
                commentary: ""
              },
              {
                move_number: 13,
                player: "W",
                move: "g4",
                commentary: "White does have the option of the ultra-aggressive 13 g4 but this is very risky."
              },
              {
                move_number: 13,
                player: "B",
                move: "h6",
                commentary: "Black should reply 13...h6."
              },
              {
                move_number: 14,
                player: "W",
                move: "h4",
                commentary: ""
              },
              {
                move_number: 14,
                player: "B",
                move: "h5!",
                commentary: "Meeting 14 h4 with ...h5!."
              }
            ]
          },
          {
            id: "game_47_side_14_a4",
            name: "Alternative 14 a4",
            description: "White plays 14 a4 to stop ...b5",
            startingMoveIndex: 8,
            moves: [
              {
                move_number: 14,
                player: "W",
                move: "a4",
                commentary: "White could also contemplate 14 a4 to stop ...b7-b5."
              },
              {
                move_number: 14,
                player: "B",
                move: "c4!",
                commentary: ""
              },
              {
                move_number: 15,
                player: "W",
                move: "Be3",
                commentary: ""
              },
              {
                move_number: 15,
                player: "B",
                move: "Nc5",
                commentary: ""
              },
              {
                move_number: 16,
                player: "W",
                move: "Bxc5",
                commentary: "Otherwise the knight infiltrates on d3."
              },
              {
                move_number: 16,
                player: "B",
                move: "Qxc5+",
                commentary: ""
              },
              {
                move_number: 17,
                player: "W",
                move: "Kh1",
                commentary: ""
              },
              {
                move_number: 17,
                player: "B",
                move: "Nd7!",
                commentary: "The black pieces co-ordinate well."
              }
            ]
          },
          {
            id: "game_47_side_16_Bf2_Kozul",
            name: "Alternative 16 Bf2 (Kozul-Nunn)",
            description: "White plays 16 Bf2. Game Kozul-Nunn, Wijk aan Zee 1991",
            startingMoveIndex: 12,
            moves: [
              {
                move_number: 16,
                player: "W",
                move: "Bf2",
                commentary: "White more or less abandoned this move after the game Kozul-Nunn."
              },
              {
                move_number: 16,
                player: "B",
                move: "Nc4",
                commentary: ""
              },
              {
                move_number: 17,
                player: "W",
                move: "Qc2",
                commentary: ""
              },
              {
                move_number: 17,
                player: "B",
                move: "Nd7",
                commentary: ""
              },
              {
                move_number: 18,
                player: "W",
                move: "Be2",
                commentary: ""
              },
              {
                move_number: 18,
                player: "B",
                move: "Rab8",
                commentary: ""
              },
              {
                move_number: 19,
                player: "W",
                move: "a4",
                commentary: ""
              },
              {
                move_number: 19,
                player: "B",
                move: "b4",
                commentary: ""
              },
              {
                move_number: 20,
                player: "W",
                move: "Bxc4?",
                commentary: "A mistake in Kozul-Nunn."
              },
              {
                move_number: 20,
                player: "B",
                move: "bxc3",
                commentary: ""
              },
              {
                move_number: 21,
                player: "W",
                move: "b3",
                commentary: ""
              },
              {
                move_number: 21,
                player: "B",
                move: "a6!",
                commentary: "This keeps the bishop out of b5."
              },
              {
                move_number: 22,
                player: "W",
                move: "Rec1",
                commentary: ""
              },
              {
                move_number: 22,
                player: "B",
                move: "Nb6",
                commentary: ""
              },
              {
                move_number: 23,
                player: "W",
                move: "Bf1",
                commentary: ""
              },
              {
                move_number: 23,
                player: "B",
                move: "c4!",
                commentary: ""
              },
              {
                move_number: 24,
                player: "W",
                move: "Bxc4",
                commentary: ""
              },
              {
                move_number: 24,
                player: "B",
                move: "Nxc4",
                commentary: ""
              },
              {
                move_number: 25,
                player: "W",
                move: "bxc4",
                commentary: ""
              },
              {
                move_number: 25,
                player: "B",
                move: "Rb2",
                commentary: "With a winning position for Black."
              }
            ]
          },
          {
            id: "game_47_side_16_Bf2_Vaisser",
            name: "Alternative 16 Bf2 (Vaisser analysis)",
            description: "White plays 16 Bf2. Vaisser tries 20 Nb5!",
            startingMoveIndex: 12,
            moves: [
              {
                move_number: 16,
                player: "W",
                move: "Bf2",
                commentary: ""
              },
              {
                move_number: 16,
                player: "B",
                move: "Nc4",
                commentary: ""
              },
              {
                move_number: 17,
                player: "W",
                move: "Qc2",
                commentary: ""
              },
              {
                move_number: 17,
                player: "B",
                move: "Nd7",
                commentary: ""
              },
              {
                move_number: 18,
                player: "W",
                move: "Be2",
                commentary: ""
              },
              {
                move_number: 18,
                player: "B",
                move: "Rab8",
                commentary: ""
              },
              {
                move_number: 19,
                player: "W",
                move: "a4",
                commentary: ""
              },
              {
                move_number: 19,
                player: "B",
                move: "b4",
                commentary: ""
              },
              {
                move_number: 20,
                player: "W",
                move: "Nb5!",
                commentary: "Vaisser gives this as unclear."
              },
              {
                move_number: 20,
                player: "B",
                move: "Nxb2",
                commentary: ""
              },
              {
                move_number: 21,
                player: "W",
                move: "Nxd6",
                commentary: ""
              },
              {
                move_number: 21,
                player: "B",
                move: "b3",
                commentary: ""
              },
              {
                move_number: 22,
                player: "W",
                move: "Qb1",
                commentary: ""
              },
              {
                move_number: 22,
                player: "B",
                move: "Nxa4",
                commentary: ""
              },
              {
                move_number: 23,
                player: "W",
                move: "Ra3!",
                commentary: "To be honest, nobody really knows what's going on."
              }
            ]
          }
        ]
      }
    }
  ]
};

fs.writeFileSync('/Users/lfesch/work_files/chess/parsed_pages_121_125.json', JSON.stringify(file, null, 2), 'utf-8');
console.log("JSON generated successfully!");
