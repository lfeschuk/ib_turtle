import json

data = {
  "book_title": "Starting Out: The King's Indian",
  "exercises": [
    {
      "id": "game_17_koutsin_frolov_1995",
      "title": "Game 17: Koutsin vs. Frolov (Kiev 1995)",
      "description": "Illustrative Game for 10 Be3 with 13...a5!?. Black blocks the queenside but White manages to launch a counter-attack, which Black meets with a thematic piece sacrifice on h3. A wild tactical battle ends in a draw.",
      "textContext": "Page 55-57 of Starting Out: The King's Indian",
      "preparsedJson": {
        "game_id": "game_17",
        "white": "Koutsin",
        "black": "Frolov",
        "event": "Kiev 1995",
        "initial_moves": "d4 Nf6 c4 g6 Nc3 Bg7 e4 d6 Nf3 O-O Be2 e5 O-O Nc6 d5 Ne7 Ne1 Nd7 Be3 f5 f3 f4 12 Bf2 g5",
        "interactive_section": {
          "starting_move": 13,
          "moves": [
            { "move_number": 13, "player": "W", "move": "a4", "commentary": "" },
            { "move_number": 13, "player": "B", "move": "a5!?", "commentary": "This is an attempt to punish White for his move order. By blocking the queenside with ...a7-a5 and ...b7-b6 Black makes it very difficult for White to achieve his most dangerous queenside advance c4-c5." },
            { "move_number": 14, "player": "W", "move": "Nd3", "commentary": "" },
            { "move_number": 14, "player": "B", "move": "b6", "commentary": "The consistent follow-up. There is no point playing ...a7-a5 if Black just allows White to play c4-c5 afterwards." },
            { "move_number": 15, "player": "W", "move": "b4", "commentary": "White must play b2-b4 at some point but there is a school of thought which believes that White should first shore up his kingside defences with 15 Be1 h5 16 Nf2 Nf6 17 h3 and only then play b4. As usual Black will aim for ...g5-g4." },
            { "move_number": 15, "player": "B", "move": "axb4", "commentary": "" },
            { "move_number": 16, "player": "W", "move": "Nb5", "commentary": "The immediate 16 Nxb4 is also possible with an unclear position." },
            { "move_number": 16, "player": "B", "move": "Nf6", "commentary": "" },
            { "move_number": 17, "player": "W", "move": "Be1?!", "commentary": "The plan of taking on b4 with the bishop looks too optimistic. It was still possible to play 17 Nxb4, meeting 17...g4 with 18 Bh4!. Black should probably play one solid move, 17...Bd7, before embarking on his kingside attack." },
            { "move_number": 17, "player": "B", "move": "g4", "commentary": "" },
            { "move_number": 18, "player": "W", "move": "Bxb4", "commentary": "Because the knight on b5 no longer protects e4 (as it did from c3) Black was able to play ...g5-g4 without further preamble. After 18 fxg4 Nxe4 Black's central pawns are potentially deadly." },
            { "move_number": 18, "player": "B", "move": "g3", "commentary": "" },
            { "move_number": 19, "player": "W", "move": "h3", "commentary": "" },
            { "move_number": 19, "player": "B", "move": "Bxh3!", "commentary": "(Diagram 15) This bishop was born to lay down its life on h3. If Black delays then White will reinforce his defences with Re1 and Bf1. There is no reason to delay!" },
            { "move_number": 20, "player": "W", "move": "gxh3", "commentary": "" },
            { "move_number": 20, "player": "B", "move": "Qd7", "commentary": "" },
            { "move_number": 21, "player": "W", "move": "Qc2", "commentary": "The only variation that Black needed to calculate before sacrificing is 21 Kg2? Ng6 22 Rh1 Nh4+ 23 Kg1 Nxe4! 24 fxe4 f3 and White gets blown away. He didn't need to look at anything else because if White can't play Kg2 then Black will pick up the crucial pawn on h3." },
            { "move_number": 21, "player": "B", "move": "Qxh3", "commentary": "" },
            { "move_number": 22, "player": "W", "move": "Bd1", "commentary": "" },
            { "move_number": 22, "player": "B", "move": "Ng6", "commentary": "" },
            { "move_number": 23, "player": "W", "move": "Qg2", "commentary": "" },
            { "move_number": 23, "player": "B", "move": "Qh6!", "commentary": "" },
            { "move_number": 24, "player": "W", "move": "Qh1", "commentary": "" },
            { "move_number": 24, "player": "B", "move": "Nh4", "commentary": "" },
            { "move_number": 25, "player": "W", "move": "Ne1", "commentary": "If White can play just one more move, 26 Ng2, then he can beat off the attack. It's time for another sacrifice to keep up the momentum." },
            { "move_number": 25, "player": "B", "move": "Nxe4!", "commentary": "" },
            { "move_number": 26, "player": "W", "move": "Ng2!", "commentary": "(Diagram 16) 26 fxe4 f3 is completely hopeless for White." },
            { "move_number": 26, "player": "B", "move": "Rf5?!", "commentary": "Black had another fascinating possibility: 26...Nxf3+! 27 Bxf3/Qxh1+ 28 Kxh1 Nf2+ 29 Rxf2/gxf2 30 Rf1/Rxa4 31 Ba3/Rxc4 32 Rxf2 and the rook and five pawns should beat the three minor pieces. This looks more convincing than Black's choice in the game." },
            { "move_number": 27, "player": "W", "move": "fxe4", "commentary": "" },
            { "move_number": 27, "player": "B", "move": "f3", "commentary": "" },
            { "move_number": 28, "player": "W", "move": "Bxf3", "commentary": "" },
            { "move_number": 28, "player": "B", "move": "Nxf3+", "commentary": "" },
            { "move_number": 29, "player": "W", "move": "Rxf3", "commentary": "" },
            { "move_number": 29, "player": "B", "move": "Qxh1+", "commentary": "" },
            { "move_number": 30, "player": "W", "move": "Kxh1", "commentary": "" },
            { "move_number": 30, "player": "B", "move": "Rxf3", "commentary": "" },
            { "move_number": 31, "player": "W", "move": "Kg1!", "commentary": "Not falling for 31 Nxc7/Rxa4! 32 Rxa4/Rf1 mate." },
            { "move_number": 31, "player": "B", "move": "Rb3?", "commentary": "Black needed one careful defensive move to keep the advantage. 31...Bf8 32 Nxc7/Rc8 it is important that the d6-pawn is defended." },
            { "move_number": 32, "player": "W", "move": "Nxc7!", "commentary": "" },
            { "move_number": 32, "player": "B", "move": "Rf8", "commentary": "" },
            { "move_number": 33, "player": "W", "move": "Be1?!", "commentary": "" },
            { "move_number": 33, "player": "B", "move": "Bf6!", "commentary": "" },
            { "move_number": 34, "player": "W", "move": "Nb5", "commentary": "" },
            { "move_number": 34, "player": "B", "move": "Be7", "commentary": "" },
            { "move_number": 35, "player": "W", "move": "Ra3", "commentary": "" },
            { "move_number": 35, "player": "B", "move": "Rxa3", "commentary": "" },
            { "move_number": 36, "player": "W", "move": "Nxa3", "commentary": "" },
            { "move_number": 36, "player": "B", "move": "Rf3", "commentary": "" },
            { "move_number": 37, "player": "W", "move": "Nc2", "commentary": "" },
            { "move_number": 37, "player": "B", "move": "Bg5", "commentary": "" },
            { "move_number": 38, "player": "W", "move": "Bb4", "commentary": "" },
            { "move_number": 38, "player": "B", "move": "h5", "commentary": "" },
            { "move_number": 39, "player": "W", "move": "Nge1", "commentary": "" },
            { "move_number": 39, "player": "B", "move": "Rf6", "commentary": "" },
            { "move_number": 40, "player": "W", "move": "a5", "commentary": "" },
            { "move_number": 40, "player": "B", "move": "bxa5", "commentary": "" },
            { "move_number": 41, "player": "W", "move": "Bxa5", "commentary": "" },
            { "move_number": 41, "player": "B", "move": "Rf2", "commentary": "" },
            { "move_number": 42, "player": "W", "move": "Bc7", "commentary": "" },
            { "move_number": 42, "player": "B", "move": "Be7", "commentary": "" },
            { "move_number": 43, "player": "W", "move": "Nd3", "commentary": "" },
            { "move_number": 43, "player": "B", "move": "Re2", "commentary": "" },
            { "move_number": 44, "player": "W", "move": "N1g2", "commentary": "" },
            { "move_number": 44, "player": "B", "move": "Ra2", "commentary": "" },
            { "move_number": 45, "player": "W", "move": "c5", "commentary": "" },
            { "move_number": 45, "player": "B", "move": "Ra1+", "commentary": "" },
            { "move_number": 46, "player": "W", "move": "Ne1", "commentary": "" },
            { "move_number": 46, "player": "B", "move": "h4", "commentary": "" },
            { "move_number": 47, "player": "W", "move": "Nxh4", "commentary": "" },
            { "move_number": 47, "player": "B", "move": "Bxh4", "commentary": "" },
            { "move_number": 48, "player": "W", "move": "Bxd6", "commentary": "" },
            { "move_number": 48, "player": "B", "move": "Re1", "commentary": "" },
            { "move_number": 49, "player": "W", "move": "c6", "commentary": "" },
            { "move_number": 49, "player": "B", "move": "Rxe4", "commentary": "" },
            { "move_number": 50, "player": "W", "move": "c7", "commentary": "" },
            { "move_number": 50, "player": "B", "move": "Rc4", "commentary": "" },
            { "move_number": 51, "player": "W", "move": "Bxe5", "commentary": "" },
            { "move_number": 51, "player": "B", "move": "Kf7", "commentary": "" },
            { "move_number": 52, "player": "W", "move": "Nxg3", "commentary": "" },
            { "move_number": 52, "player": "B", "move": "Bxg3", "commentary": "Draw agreed" }
          ]
        },
        "sidelines": [
          {
            "id": "game_17_side_1",
            "name": "Alternative 15 Be1",
            "description": "White shores up kingside defences before b4.",
            "startingMoveIndex": 3,
            "moves": [
              { "move_number": 15, "player": "W", "move": "Be1", "commentary": "" },
              { "move_number": 15, "player": "B", "move": "h5", "commentary": "" },
              { "move_number": 16, "player": "W", "move": "Nf2", "commentary": "" },
              { "move_number": 16, "player": "B", "move": "Nf6", "commentary": "" },
              { "move_number": 17, "player": "W", "move": "h3", "commentary": "And only then play b4." }
            ]
          },
          {
            "id": "game_17_side_2",
            "name": "Alternative 16 Nxb4",
            "description": "White plays 16 Nxb4 instead of 16 Nb5.",
            "startingMoveIndex": 5,
            "moves": [
              { "move_number": 16, "player": "W", "move": "Nxb4", "commentary": "With an unclear position." }
            ]
          },
          {
            "id": "game_17_side_3",
            "name": "Alternative 17 Nxb4",
            "description": "White plays 17 Nxb4 instead of 17 Be1?!.",
            "startingMoveIndex": 7,
            "moves": [
              { "move_number": 17, "player": "W", "move": "Nxb4", "commentary": "Meeting 17...g4 with 18 Bh4!." }
            ]
          },
          {
            "id": "game_17_side_4",
            "name": "Alternative 17...Bd7",
            "description": "Black plays 17...Bd7 instead of 17...g4.",
            "startingMoveIndex": 8,
            "moves": [
              { "move_number": 17, "player": "B", "move": "Bd7", "commentary": "Before embarking on his kingside attack." }
            ]
          },
          {
            "id": "game_17_side_5",
            "name": "Alternative 21 Kg2?",
            "description": "White plays 21 Kg2? instead of 21 Qc2.",
            "startingMoveIndex": 15,
            "moves": [
              { "move_number": 21, "player": "W", "move": "Kg2?", "commentary": "" },
              { "move_number": 21, "player": "B", "move": "Ng6", "commentary": "" },
              { "move_number": 22, "player": "W", "move": "Rh1", "commentary": "" },
              { "move_number": 22, "player": "B", "move": "Nh4+", "commentary": "" },
              { "move_number": 23, "player": "W", "move": "Kg1", "commentary": "" },
              { "move_number": 23, "player": "B", "move": "Nxe4!", "commentary": "" },
              { "move_number": 24, "player": "W", "move": "fxe4", "commentary": "" },
              { "move_number": 24, "player": "B", "move": "f3", "commentary": "And White gets blown away." }
            ]
          },
          {
            "id": "game_17_side_6",
            "name": "Alternative 26...Nxf3+!",
            "description": "Black plays 26...Nxf3+! instead of 26...Rf5?!.",
            "startingMoveIndex": 26,
            "moves": [
              { "move_number": 26, "player": "B", "move": "Nxf3+!", "commentary": "" },
              { "move_number": 27, "player": "W", "move": "Bxf3", "commentary": "" },
              { "move_number": 27, "player": "B", "move": "Qxh1+", "commentary": "" },
              { "move_number": 28, "player": "W", "move": "Kxh1", "commentary": "" },
              { "move_number": 28, "player": "B", "move": "Nf2+", "commentary": "" },
              { "move_number": 29, "player": "W", "move": "Rxf2", "commentary": "" },
              { "move_number": 29, "player": "B", "move": "gxf2", "commentary": "" },
              { "move_number": 30, "player": "W", "move": "Rf1", "commentary": "" },
              { "move_number": 30, "player": "B", "move": "Rxa4", "commentary": "" },
              { "move_number": 31, "player": "W", "move": "Ba3", "commentary": "" },
              { "move_number": 31, "player": "B", "move": "Rxc4", "commentary": "" },
              { "move_number": 32, "player": "W", "move": "Rxf2", "commentary": "And the rook and five pawns should beat the three minor pieces." }
            ]
          },
          {
            "id": "game_17_side_7",
            "name": "Alternative 31...Bf8",
            "description": "Black plays 31...Bf8 instead of 31...Rb3?.",
            "startingMoveIndex": 36,
            "moves": [
              { "move_number": 31, "player": "B", "move": "Bf8", "commentary": "" },
              { "move_number": 32, "player": "W", "move": "Nxc7", "commentary": "" },
              { "move_number": 32, "player": "B", "move": "Rc8", "commentary": "It is important that the d6-pawn is defended." }
            ]
          }
        ]
      }
    },
    {
      "id": "game_18_borges_mateos_pecorelli_2000",
      "title": "Game 18: Borges Mateos vs. Pecorelli (Cali 2000)",
      "description": "Illustrative Game for 10 Be3 with 13 Rc1 Rf6!. Shows White trying to play a slower, solid setup on the queenside, but Black's direct rook lift to Rh6 leads to a devastating kingside attack, culminating in a beautiful queen sacrifice.",
      "textContext": "Page 57-58 of Starting Out: The King's Indian",
      "preparsedJson": {
        "game_id": "game_18",
        "white": "Borges Mateos",
        "black": "Pecorelli",
        "event": "Cali 2000",
        "initial_moves": "d4 Nf6 c4 g6 Nc3 Bg7 e4 d6 Nf3 O-O Be2 e5 O-O Nc6 d5 Ne7 Ne1 Nd7 Be3 f5 f3 f4 12 Bf2 g5 13 Rc1 Rf6!",
        "interactive_section": {
          "starting_move": 14,
          "moves": [
            { "move_number": 14, "player": "W", "move": "Nd3", "commentary": "" },
            { "move_number": 14, "player": "B", "move": "Rh6", "commentary": "(Diagram 17)" },
            { "move_number": 15, "player": "W", "move": "b4", "commentary": "" },
            { "move_number": 15, "player": "B", "move": "Qe8", "commentary": "" },
            { "move_number": 16, "player": "W", "move": "c5?", "commentary": "16 Kh1 was necessary to defend against the kingside attack." },
            { "move_number": 16, "player": "B", "move": "Qh5", "commentary": "" },
            { "move_number": 17, "player": "W", "move": "h3", "commentary": "" },
            { "move_number": 17, "player": "B", "move": "Nxc5!", "commentary": "" },
            { "move_number": 18, "player": "W", "move": "Bxc5", "commentary": "" },
            { "move_number": 18, "player": "B", "move": "Bxh3!", "commentary": "" },
            { "move_number": 19, "player": "W", "move": "Nf2", "commentary": "" },
            { "move_number": 19, "player": "B", "move": "Bxg2!", "commentary": "" },
            { "move_number": 20, "player": "W", "move": "Ng4", "commentary": "" },
            { "move_number": 20, "player": "B", "move": "Qh1+", "commentary": "" },
            { "move_number": 21, "player": "W", "move": "Kf2", "commentary": "" },
            { "move_number": 21, "player": "B", "move": "Qh4+", "commentary": "" },
            { "move_number": 22, "player": "W", "move": "Kg1", "commentary": "" },
            { "move_number": 22, "player": "B", "move": "Rh5", "commentary": "White resigns." }
          ]
        },
        "sidelines": [
          {
            "id": "game_18_side_1",
            "name": "Alternative 16 Kh1",
            "description": "White plays 16 Kh1 instead of 16 c5?.",
            "startingMoveIndex": 3,
            "moves": [
              { "move_number": 16, "player": "W", "move": "Kh1", "commentary": "This was necessary." }
            ]
          },
          {
            "id": "game_18_side_2",
            "name": "Alternative 23 Qe1",
            "description": "White plays 23 Qe1 to stop mate.",
            "startingMoveIndex": 17,
            "moves": [
              { "move_number": 23, "player": "W", "move": "Qe1", "commentary": "Only move to stop mate." },
              { "move_number": 23, "player": "B", "move": "Qg3", "commentary": "But after 23...Qg3 Black will soon be winning on material, if nothing else, as White can't save the bishop on c5 or the rook on f1." }
            ]
          }
        ]
      }
    },
    {
      "id": "game_19_opalic_socko_1999",
      "title": "Game 19: Opalic vs. Socko (Passau 1999)",
      "description": "Illustrative Game for 10 Be3 with 13 Rc1 Rf6!. Similar to Game 18 but here Black plays 15...a6 to prevent Nb5. White attempts to defend by retreating the knight to d3 and e1, but Black's attack cannot be stopped, leading to another checkmate win.",
      "textContext": "Page 58-59 of Starting Out: The King's Indian",
      "preparsedJson": {
        "game_id": "game_19",
        "white": "Opalic",
        "black": "Socko",
        "event": "Passau 1999",
        "initial_moves": "d4 Nf6 2 Nf3 g6 3 c4 Bg7 4 Nc3 O-O 5 e4 d6 6 Be2 e5 7 O-O Nc6 8 d5 Ne7 9 Ne1 Nd7 10 Be3 f5 11 f3 f4 12 Bf2 g5 13 Rc1 Rf6! 14 b4 Rh6 15 c5",
        "interactive_section": {
          "starting_move": 15,
          "moves": [
            { "move_number": 15, "player": "B", "move": "a6", "commentary": "This has been played on several occasions to prevent Nb5 but I don't see the need for it. For example, after 15...Qe8! 16 Nb5 Qh5..." },
            { "move_number": 16, "player": "W", "move": "Na4", "commentary": "Instead of 16 Nb5 White can play 16 Kh1 and now Black should play 16...Nf6! and after 17 Nb5? (17 Nd3 is better) 17...Qh5 18 Bg1." },
            { "move_number": 16, "player": "B", "move": "Qe8", "commentary": "" },
            { "move_number": 17, "player": "W", "move": "Kh1", "commentary": "" },
            { "move_number": 17, "player": "B", "move": "Kh8!?", "commentary": "" },
            { "move_number": 18, "player": "W", "move": "cxd6", "commentary": "" },
            { "move_number": 18, "player": "B", "move": "cxd6", "commentary": "" },
            { "move_number": 19, "player": "W", "move": "Rc7", "commentary": "" },
            { "move_number": 19, "player": "B", "move": "b5", "commentary": "" },
            { "move_number": 20, "player": "W", "move": "Nb2", "commentary": "" },
            { "move_number": 20, "player": "B", "move": "Nf6", "commentary": "" },
            { "move_number": 21, "player": "W", "move": "a4", "commentary": "" },
            { "move_number": 21, "player": "B", "move": "Qh5", "commentary": "" },
            { "move_number": 22, "player": "W", "move": "Bg1", "commentary": "(Diagram 20)" },
            { "move_number": 22, "player": "B", "move": "Nfxd5!", "commentary": "" },
            { "move_number": 23, "player": "W", "move": "Rxc8+", "commentary": "" },
            { "move_number": 23, "player": "B", "move": "Rxc8", "commentary": "" },
            { "move_number": 24, "player": "W", "move": "exd5", "commentary": "" },
            { "move_number": 24, "player": "B", "move": "Nf5", "commentary": "" },
            { "move_number": 25, "player": "W", "move": "h3", "commentary": "" },
            { "move_number": 25, "player": "B", "move": "e4", "commentary": "" },
            { "move_number": 26, "player": "W", "move": "Kh2", "commentary": "" },
            { "move_number": 26, "player": "B", "move": "e3", "commentary": "" },
            { "move_number": 27, "player": "W", "move": "Nbd3", "commentary": "" },
            { "move_number": 27, "player": "B", "move": "Nh4", "commentary": "White resigns." }
          ]
        },
        "sidelines": [
          {
            "id": "game_19_side_1",
            "name": "Alternative 15...Qe8!",
            "description": "Black plays 15...Qe8! instead of 15...a6.",
            "startingMoveIndex": -1,
            "moves": [
              { "move_number": 15, "player": "B", "move": "Qe8!", "commentary": "" },
              { "move_number": 16, "player": "W", "move": "Nb5", "commentary": "" },
              { "move_number": 16, "player": "B", "move": "Qh5", "commentary": "" },
              { "move_number": 17, "player": "W", "move": "h4", "commentary": "White's only move to stop mate. If 17 h3 Bxh3!." },
              { "move_number": 17, "player": "B", "move": "gxh4", "commentary": "Followed by ...h4-h3 with a very strong attack." }
            ]
          },
          {
            "id": "game_19_side_2",
            "name": "Alternative 15...Qe8! with 16 Kh1",
            "description": "Black plays 15...Qe8! and White replies 16 Kh1 instead of 16 Nb5.",
            "startingMoveIndex": -1,
            "moves": [
              { "move_number": 15, "player": "B", "move": "Qe8!", "commentary": "" },
              { "move_number": 16, "player": "W", "move": "Kh1", "commentary": "" },
              { "move_number": 16, "player": "B", "move": "Nf6!", "commentary": "" },
              { "move_number": 17, "player": "W", "move": "Nd3", "commentary": "Better than 17 Nb5?." }
            ]
          },
          {
            "id": "game_19_side_3",
            "name": "Alternative 15...Qe8! with 16 Kh1 and 17 Nb5?",
            "description": "In the 15...Qe8! line with 16 Kh1, White plays 17 Nb5? instead of 17 Nd3.",
            "startingMoveIndex": -1,
            "moves": [
              { "move_number": 15, "player": "B", "move": "Qe8!", "commentary": "" },
              { "move_number": 16, "player": "W", "move": "Kh1", "commentary": "" },
              { "move_number": 16, "player": "B", "move": "Nf6!", "commentary": "" },
              { "move_number": 17, "player": "W", "move": "Nb5?", "commentary": "" },
              { "move_number": 17, "player": "B", "move": "Qh5", "commentary": "" },
              { "move_number": 18, "player": "W", "move": "Bg1", "commentary": "" }
            ]
          },
          {
            "id": "game_19_side_4",
            "name": "Alternative 23 exd5",
            "description": "White plays 23 exd5 instead of 23 Rxc8+.",
            "startingMoveIndex": 14,
            "moves": [
              { "move_number": 23, "player": "W", "move": "exd5", "commentary": "" },
              { "move_number": 23, "player": "B", "move": "Nf5", "commentary": "" },
              { "move_number": 24, "player": "W", "move": "h3", "commentary": "" },
              { "move_number": 24, "player": "B", "move": "Ng3+", "commentary": "" },
              { "move_number": 25, "player": "W", "move": "Kh2", "commentary": "The bishop would have sacrificed itself on h3." }
            ]
          }
        ]
      }
    }
  ]
}

with open("/Users/lfesch/work_files/chess/parsed_pages_56_60.json", "w") as f:
    json.dump(data, f, indent=2)

print("JSON file created successfully.")
