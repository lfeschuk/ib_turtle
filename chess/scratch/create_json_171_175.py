import json

data = {
    "book_title": "Starting Out: The King's Indian",
    "exercises": []
}

# Exercise 1: Game 66 (continued from printed page 170 / PDF page 171)
ex1 = {
    "id": "game_66_liardet_gallagher_1998_cont",
    "title": "Game 66: Liardet vs. Gallagher (Lenk 1998) (continued)",
    "description": "Continuation and conclusion of Game 66 from page 170. Black counters White's queenside plans and launches a winning kingside counter-attack.",
    "textContext": "Page 170",
    "preparsedJson": {
        "game_id": "game_66_cont",
        "white": "Liardet",
        "black": "Gallagher",
        "event": "Lenk 1998",
        "initial_moves": "1 d4 Nf6 2 c4 g6 3 Nc3 Bg7 4 e4 d6 5 Nge2 a6 6 Ng3 c6 7 Be2",
        "interactive_section": {
            "starting_move": 7,
            "moves": [
                {"move_number": 7, "player": "B", "move": "b5", "commentary": "Black initiates queenside counterplay."},
                {"move_number": 8, "player": "W", "move": "cxb5", "commentary": ""},
                {"move_number": 8, "player": "B", "move": "axb5", "commentary": ""},
                {"move_number": 9, "player": "W", "move": "b4", "commentary": ""},
                {"move_number": 9, "player": "B", "move": "O-O", "commentary": ""},
                {"move_number": 10, "player": "W", "move": "Rb1", "commentary": "I'm not too convinced by White's plan. He is playing half-heartedly on both wings."},
                {"move_number": 10, "player": "B", "move": "Nbd7", "commentary": ""},
                {"move_number": 11, "player": "W", "move": "O-O", "commentary": ""},
                {"move_number": 11, "player": "B", "move": "Bb7", "commentary": ""},
                {"move_number": 12, "player": "W", "move": "Bg5", "commentary": ""},
                {"move_number": 12, "player": "B", "move": "h6", "commentary": ""},
                {"move_number": 13, "player": "W", "move": "Be3", "commentary": ""},
                {"move_number": 13, "player": "B", "move": "e5", "commentary": ""},
                {"move_number": 14, "player": "W", "move": "Qc2", "commentary": ""},
                {"move_number": 14, "player": "B", "move": "Qe7", "commentary": ""},
                {"move_number": 15, "player": "W", "move": "Rfd1", "commentary": ""},
                {"move_number": 15, "player": "B", "move": "exd4", "commentary": ""},
                {"move_number": 16, "player": "W", "move": "Bxd4", "commentary": ""},
                {"move_number": 16, "player": "B", "move": "h5", "commentary": ""},
                {"move_number": 17, "player": "W", "move": "f3", "commentary": ""},
                {"move_number": 17, "player": "B", "move": "Ne5", "commentary": "(Diagram 9)"},
                {"move_number": 18, "player": "W", "move": "Nf1", "commentary": ""},
                {"move_number": 18, "player": "B", "move": "h4", "commentary": ""},
                {"move_number": 19, "player": "W", "move": "Qd2", "commentary": ""},
                {"move_number": 19, "player": "B", "move": "Rfe8", "commentary": ""},
                {"move_number": 20, "player": "W", "move": "Bf2", "commentary": ""},
                {"move_number": 20, "player": "B", "move": "Nh5!", "commentary": ""},
                {"move_number": 21, "player": "W", "move": "g4", "commentary": "21 Qxd6 Qg5 with ...Nf4 to follow is much too dangerous for White. I wasn't too unhappy to see the text either as the white king position is beginning to open up."},
                {"move_number": 21, "player": "B", "move": "hxg3", "commentary": ""},
                {"move_number": 22, "player": "W", "move": "hxg3", "commentary": ""},
                {"move_number": 22, "player": "B", "move": "Rad8", "commentary": ""},
                {"move_number": 23, "player": "W", "move": "g4", "commentary": ""},
                {"move_number": 23, "player": "B", "move": "Nf6", "commentary": ""},
                {"move_number": 24, "player": "W", "move": "Ng3", "commentary": ""},
                {"move_number": 24, "player": "B", "move": "Qe6", "commentary": ""},
                {"move_number": 25, "player": "W", "move": "Kg2", "commentary": "White should have played 25 g5. Now he is losing."},
                {"move_number": 25, "player": "B", "move": "d5!", "commentary": ""},
                {"move_number": 26, "player": "W", "move": "g5", "commentary": "(Diagram 10)"},
                {"move_number": 26, "player": "B", "move": "Nxf3!", "commentary": "White had seen that 26...dxe4 27 Qxd8 wasn't so clear but completely overlooked this shot. Of course 27 Bxf3 just loses to 27...dxe4."},
                {"move_number": 27, "player": "W", "move": "Qf4", "commentary": ""},
                {"move_number": 27, "player": "B", "move": "Nxe4!", "commentary": "If White takes on f3 Black takes on c3 and if White takes on e4 Black recaptures defending his knight on f3."},
                {"move_number": 28, "player": "W", "move": "Ncxe4", "commentary": ""},
                {"move_number": 28, "player": "B", "move": "dxe4", "commentary": ""},
                {"move_number": 29, "player": "W", "move": "Nxe4", "commentary": ""},
                {"move_number": 29, "player": "B", "move": "Nd4", "commentary": ""},
                {"move_number": 30, "player": "W", "move": "Bxd4", "commentary": ""},
                {"move_number": 30, "player": "B", "move": "Rxd4", "commentary": ""},
                {"move_number": 31, "player": "W", "move": "Bf3", "commentary": ""},
                {"move_number": 31, "player": "B", "move": "Qxa2+", "commentary": ""},
                {"move_number": 32, "player": "W", "move": "Kg1", "commentary": ""},
                {"move_number": 32, "player": "B", "move": "c5", "commentary": ""},
                {"move_number": 33, "player": "W", "move": "Nf6+", "commentary": ""},
                {"move_number": 33, "player": "B", "move": "Bxf6", "commentary": ""},
                {"move_number": 34, "player": "W", "move": "Qxf6", "commentary": ""},
                {"move_number": 34, "player": "B", "move": "Rg4+", "commentary": ""},
                {"move_number": 35, "player": "W", "move": "Kf1", "commentary": "35 Bxg4 Qg2 mate and 35 Kh1 Qf2! were alternative wins."},
                {"move_number": 35, "player": "B", "move": "Qc4+", "commentary": ""},
                {"move_number": 36, "player": "W", "move": "Kf2", "commentary": ""},
                {"move_number": 36, "player": "B", "move": "Re2+", "commentary": "White resigns. White resigned because of 37 Bxe2 Rg2+ 38 Ke3 Rxe2+."}
            ]
        },
        "sidelines": [
            {
                "id": "game_66_side_8_oo",
                "name": "Alternative 8 O-O",
                "description": "White plays 8 O-O instead of 8 cxb5.",
                "startingMoveIndex": 0,
                "moves": [
                    {
                        "move_number": 8,
                        "player": "W",
                        "move": "O-O",
                        "commentary": "However, 8 O-O O-O 9 e5! is quite good for White so Black should probably play 8...Nbd7."
                    },
                    {"move_number": 8, "player": "B", "move": "O-O", "commentary": ""},
                    {"move_number": 9, "player": "W", "move": "e5", "commentary": ""}
                ]
            },
            {
                "id": "game_66_side_8_nbd7",
                "name": "Alternative 8...Nbd7",
                "description": "Black responds with 8...Nbd7 to 8 O-O.",
                "startingMoveIndex": 0,
                "moves": [
                    {"move_number": 8, "player": "W", "move": "O-O", "commentary": ""},
                    {
                        "move_number": 8,
                        "player": "B",
                        "move": "Nbd7",
                        "commentary": "This is Black's recommended reply."
                    }
                ]
            }
        ]
    }
}

# Exercise 2: Game 67: Sharif vs. Mamedov, Abu Dhabi 2001
ex2 = {
    "id": "game_67_sharif_mamedov_2001",
    "title": "Game 67: Sharif vs. Mamedov (Abu Dhabi 2001)",
    "description": "Illustrative game for the Smyslov Variation. White develops the queen to c2 to meet e5 with Rd1, but Black gets active play and wins after positional mistakes by White.",
    "textContext": "Pages 172-173",
    "preparsedJson": {
        "game_id": "game_67",
        "white": "Sharif",
        "black": "Mamedov",
        "event": "Abu Dhabi 2001",
        "initial_moves": "1 d4 Nf6 2 c4 g6 3 Nc3 Bg7 4 Nf3 O-O 5 Bg5 d6 6 e3 Nbd7",
        "interactive_section": {
            "starting_move": 7,
            "moves": [
                {
                    "move_number": 7,
                    "player": "W",
                    "move": "Qc2!",
                    "commentary": "White wants to be able to meet ...e7-e5 with Rd1."
                },
                {"move_number": 7, "player": "B", "move": "c6", "commentary": ""},
                {"move_number": 8, "player": "W", "move": "Be2", "commentary": ""},
                {"move_number": 8, "player": "B", "move": "a6", "commentary": ""},
                {"move_number": 9, "player": "W", "move": "O-O", "commentary": ""},
                {"move_number": 9, "player": "B", "move": "h6", "commentary": ""},
                {"move_number": 10, "player": "W", "move": "Bh4", "commentary": ""},
                {"move_number": 10, "player": "B", "move": "e5", "commentary": "(Diagram 12)"},
                {"move_number": 11, "player": "W", "move": "dxe5", "commentary": "There was no reason to release the central tension. 11 Rfd1 looks like a good move."},
                {"move_number": 11, "player": "B", "move": "dxe5", "commentary": ""},
                {"move_number": 12, "player": "W", "move": "Rad1", "commentary": ""},
                {"move_number": 12, "player": "B", "move": "Qe7", "commentary": ""},
                {"move_number": 13, "player": "W", "move": "a3", "commentary": ""},
                {"move_number": 13, "player": "B", "move": "a5", "commentary": "After preparing ...b7-b5 it seems strange not to play it. Nevertheless, the position after 10...b5 11 a3 Bb7 12 Nd2 is quite unpleasant for Black."},
                {"move_number": 14, "player": "W", "move": "Nd2", "commentary": ""},
                {"move_number": 14, "player": "B", "move": "Nc5", "commentary": ""},
                {"move_number": 15, "player": "W", "move": "Nb3", "commentary": ""},
                {"move_number": 15, "player": "B", "move": "Nxb3", "commentary": ""},
                {"move_number": 16, "player": "W", "move": "Qxb3", "commentary": ""},
                {"move_number": 16, "player": "B", "move": "g5", "commentary": ""},
                {"move_number": 17, "player": "W", "move": "Bg3", "commentary": ""},
                {"move_number": 17, "player": "B", "move": "Nd7", "commentary": ""},
                {"move_number": 18, "player": "W", "move": "f3", "commentary": ""},
                {"move_number": 18, "player": "B", "move": "Nc5", "commentary": ""},
                {"move_number": 19, "player": "W", "move": "Qc2", "commentary": ""},
                {"move_number": 19, "player": "B", "move": "f5", "commentary": ""},
                {"move_number": 20, "player": "W", "move": "Kh1", "commentary": ""},
                {"move_number": 20, "player": "B", "move": "Be6", "commentary": ""},
                {"move_number": 21, "player": "W", "move": "e4", "commentary": "(Diagram 13)"},
                {"move_number": 21, "player": "B", "move": "fxe4", "commentary": ""},
                {"move_number": 22, "player": "W", "move": "Nxe4", "commentary": ""},
                {"move_number": 22, "player": "B", "move": "Bf5", "commentary": ""},
                {"move_number": 23, "player": "W", "move": "Bd3!", "commentary": ""},
                {"move_number": 23, "player": "B", "move": "Nxd3", "commentary": ""},
                {"move_number": 24, "player": "W", "move": "Qxd3", "commentary": ""},
                {"move_number": 24, "player": "B", "move": "Rad8", "commentary": ""},
                {"move_number": 25, "player": "W", "move": "Qe2", "commentary": ""},
                {"move_number": 25, "player": "B", "move": "Rfe8", "commentary": ""},
                {"move_number": 26, "player": "W", "move": "Bf2", "commentary": ""},
                {"move_number": 26, "player": "B", "move": "Bxe4", "commentary": ""},
                {"move_number": 27, "player": "W", "move": "fxe4", "commentary": ""},
                {"move_number": 27, "player": "B", "move": "Qc7", "commentary": ""},
                {"move_number": 28, "player": "W", "move": "h3", "commentary": ""},
                {"move_number": 28, "player": "B", "move": "Rxd1", "commentary": ""},
                {"move_number": 29, "player": "W", "move": "Rxd1", "commentary": ""},
                {"move_number": 29, "player": "B", "move": "Rd8", "commentary": ""},
                {"move_number": 30, "player": "W", "move": "Kg1", "commentary": ""},
                {"move_number": 30, "player": "B", "move": "Rxd1+", "commentary": ""},
                {"move_number": 31, "player": "W", "move": "Qxd1", "commentary": ""},
                {"move_number": 31, "player": "B", "move": "Bf8", "commentary": ""},
                {"move_number": 32, "player": "W", "move": "Qa4", "commentary": ""},
                {"move_number": 32, "player": "B", "move": "b6", "commentary": ""},
                {"move_number": 33, "player": "W", "move": "b4", "commentary": ""},
                {"move_number": 33, "player": "B", "move": "axb4", "commentary": ""},
                {"move_number": 34, "player": "W", "move": "axb4", "commentary": ""},
                {"move_number": 34, "player": "B", "move": "c5?", "commentary": ""},
                {"move_number": 35, "player": "W", "move": "b5", "commentary": ""},
                {"move_number": 35, "player": "B", "move": "h5?!", "commentary": ""},
                {"move_number": 36, "player": "W", "move": "Qd1", "commentary": ""},
                {"move_number": 36, "player": "B", "move": "h4", "commentary": ""},
                {"move_number": 37, "player": "W", "move": "Qd5+", "commentary": ""},
                {"move_number": 37, "player": "B", "move": "Kg7", "commentary": ""},
                {"move_number": 38, "player": "W", "move": "Be3", "commentary": "Black resigns."}
            ]
        },
        "sidelines": [
            {
                "id": "game_67_sideline_8_e5",
                "name": "Alternative 8...e5",
                "description": "Black plays 8...e5 and allows White to pin on the d-file.",
                "startingMoveIndex": 2,
                "moves": [
                    {
                        "move_number": 8,
                        "player": "B",
                        "move": "e5",
                        "commentary": "After 8...e5 9 Rd1 Qc7 10 O-O h6 11 Bh4 another one of the points of Qc2 is revealed."
                    },
                    {"move_number": 9, "player": "W", "move": "Rd1", "commentary": ""},
                    {"move_number": 9, "player": "B", "move": "Qc7", "commentary": ""},
                    {"move_number": 10, "player": "W", "move": "O-O", "commentary": ""},
                    {"move_number": 10, "player": "B", "move": "h6", "commentary": ""},
                    {"move_number": 11, "player": "W", "move": "Bh4", "commentary": ""}
                ]
            },
            {
                "id": "game_67_sideline_11_g5_refuted",
                "name": "Alternative 8...e5 with 11...g5 (Exercise 11)",
                "description": "Black tries 11...g5 to trap the bishop but is refuted by 13 Nxg5!.",
                "startingMoveIndex": 2,
                "moves": [
                    {"move_number": 8, "player": "B", "move": "e5", "commentary": ""},
                    {"move_number": 9, "player": "W", "move": "Rd1", "commentary": ""},
                    {"move_number": 9, "player": "B", "move": "Qc7", "commentary": ""},
                    {"move_number": 10, "player": "W", "move": "O-O", "commentary": ""},
                    {"move_number": 10, "player": "B", "move": "h6", "commentary": ""},
                    {"move_number": 11, "player": "W", "move": "Bh4", "commentary": ""},
                    {
                        "move_number": 11,
                        "player": "B",
                        "move": "g5",
                        "commentary": "Black tries to kick the bishop, aiming to remove White's bishop pair with ...Nh5."
                    },
                    {"move_number": 12, "player": "W", "move": "Bg3", "commentary": ""},
                    {"move_number": 12, "player": "B", "move": "Nh5", "commentary": "(Diagram 14)"},
                    {
                        "move_number": 13,
                        "player": "W",
                        "move": "Nxg5!",
                        "commentary": "A thematic tactical blow! (Refutation from Exercise 11 solution)"
                    },
                    {"move_number": 13, "player": "B", "move": "hxg5", "commentary": ""},
                    {
                        "move_number": 14,
                        "player": "W",
                        "move": "Bxh5",
                        "commentary": "White wins a crucial pawn."
                    }
                ]
            },
            {
                "id": "game_67_sideline_13_nxg3_trap",
                "name": "Alternative 13...Nxg3 in 11...g5 line",
                "description": "Black plays 13...Nxg3 but gets checkmated on h7.",
                "startingMoveIndex": 2,
                "moves": [
                    {"move_number": 8, "player": "B", "move": "e5", "commentary": ""},
                    {"move_number": 9, "player": "W", "move": "Rd1", "commentary": ""},
                    {"move_number": 9, "player": "B", "move": "Qc7", "commentary": ""},
                    {"move_number": 10, "player": "W", "move": "O-O", "commentary": ""},
                    {"move_number": 10, "player": "B", "move": "h6", "commentary": ""},
                    {"move_number": 11, "player": "W", "move": "Bh4", "commentary": ""},
                    {"move_number": 11, "player": "B", "move": "g5", "commentary": ""},
                    {"move_number": 12, "player": "W", "move": "Bg3", "commentary": ""},
                    {"move_number": 12, "player": "B", "move": "Nh5", "commentary": ""},
                    {"move_number": 13, "player": "W", "move": "Nxg5!",
                        "commentary": ""},
                    {
                        "move_number": 13,
                        "player": "B",
                        "move": "Nxg3",
                        "commentary": "Normally Black could meet 13 Nxg5 with this, but he can't here as White is also threatening mate on h7."
                    },
                    {"move_number": 14, "player": "W", "move": "Qh7#", "commentary": "Checkmate."}
                ]
            },
            {
                "id": "game_67_sideline_21_f4",
                "name": "Alternative 21...f4",
                "description": "Black tries 21...f4 to lock the kingside, but is refuted by 23 Nd5!.",
                "startingMoveIndex": 27,
                "moves": [
                    {"move_number": 21, "player": "W", "move": "e4", "commentary": ""},
                    {
                        "move_number": 21,
                        "player": "B",
                        "move": "f4",
                        "commentary": "Note how White only played e4 when the knight on c5 could no longer go to e6. It was possible for Black to play 21...f4 but after 22 Bf2 Rad8 White can play 23 Nd5! cxd5 24 cxd5 when he regains the piece with a sizeable advantage."
                    },
                    {"move_number": 22, "player": "W", "move": "Bf2", "commentary": ""},
                    {"move_number": 22, "player": "B", "move": "Rad8", "commentary": ""},
                    {"move_number": 23, "player": "W", "move": "Nd5!", "commentary": ""},
                    {"move_number": 23, "player": "B", "move": "cxd5", "commentary": ""},
                    {"move_number": 24, "player": "W", "move": "cxd5", "commentary": ""}
                ]
            }
        ]
    }
}

# Exercise 3: Game 68: Pachman vs. Smyslov, Amsterdam 1994
ex3 = {
    "id": "game_68_pachman_smyslov_1994",
    "title": "Game 68: Pachman vs. Smyslov (Amsterdam 1994)",
    "description": "Illustrative game for the Smyslov Variation. Smyslov demonstrates his own defence to the Smyslov variation, playing an early ...c5, ...h6, and a beautiful tactical combination starting with 14...Nbxd5!.",
    "textContext": "Pages 173-174",
    "preparsedJson": {
        "game_id": "game_68",
        "white": "Pachman",
        "black": "Smyslov",
        "event": "Amsterdam 1994",
        "initial_moves": "1 d4 Nf6 2 c4 g6 3 Nc3 Bg7 4 Nf3 O-O 5 Bg5 d6 6 e3 c5",
        "interactive_section": {
            "starting_move": 7,
            "moves": [
                {
                    "move_number": 7,
                    "player": "W",
                    "move": "Be2",
                    "commentary": "After 7 dxc5 dxc5 8 Qxd8 Rxd8 White would have to play well to draw the endgame. Sometimes White blocks the centre with 7 d5 when 7...h6 8 Bh4 e5 would be standard play, but Black could also try 8...Qb6, hoping to reach similar positions to the main line."
                },
                {"move_number": 7, "player": "B", "move": "h6", "commentary": ""},
                {"move_number": 8, "player": "W", "move": "Bh4", "commentary": ""},
                {"move_number": 8, "player": "B", "move": "Bf5!?", "commentary": "(Diagram 14) There are a couple of good reasons for putting the bishop on f5. Firstly it enables Black to play ...Ne4. After the knights on f6 and c3 have disappeared the bishop on g7 becomes very powerful. The second reason is that it covers b1 and in a surprising number of variations this allows Black to mount a decisive assault against the b2-pawn."},
                {"move_number": 9, "player": "W", "move": "O-O", "commentary": ""},
                {
                    "move_number": 9,
                    "player": "B",
                    "move": "Nbd7!?",
                    "commentary": "Preparing ...Qb6, which is not playable at once in view of 10 Bxf6 followed by Nd5. The immediate 9...Ne4 is an interesting alternative."
                },
                {
                    "move_number": 10,
                    "player": "W",
                    "move": "d5?!",
                    "commentary": "A strange decision. 10 Rc1 is more logical so that White can meet 10...Qb6 with 11 b3."
                },
                {"move_number": 10, "player": "B", "move": "Qb6!", "commentary": ""},
                {
                    "move_number": 11,
                    "player": "W",
                    "move": "Na4",
                    "commentary": "Not a good square for the knight."
                },
                {"move_number": 11, "player": "B", "move": "Qa5", "commentary": ""},
                {"move_number": 12, "player": "W", "move": "Nd2", "commentary": ""},
                {"move_number": 12, "player": "B", "move": "Nb6", "commentary": ""},
                {"move_number": 13, "player": "W", "move": "Nc3", "commentary": "13 Nxb6 Qxb6 again leaves the b-pawn in difficulties. Now White hopes that his problems can be solved by advancing e4, but Smyslov was ready for that one."},
                {"move_number": 13, "player": "B", "move": "Qb4!", "commentary": ""},
                {
                    "move_number": 14,
                    "player": "W",
                    "move": "Qb3",
                    "commentary": "White defends the b2-pawn."
                },
                {
                    "move_number": 14,
                    "player": "B",
                    "move": "Nbxd5!",
                    "commentary": "(Diagram 15) And now we know why Smyslov didn't succumb to any urge he may have felt to play ...g6-g5. The exposed position of the bishop on h4 is the key point in this simple, but pleasing combination."
                },
                {"move_number": 15, "player": "W", "move": "cxd5", "commentary": ""},
                {"move_number": 15, "player": "B", "move": "Qxh4", "commentary": ""},
                {"move_number": 16, "player": "W", "move": "Qxb7", "commentary": ""},
                {"move_number": 16, "player": "B", "move": "Qb4!", "commentary": "Black's last few moves illustrate well the power of the queen."},
                {"move_number": 17, "player": "W", "move": "Qxb4", "commentary": "There is no choice for White as 17 Qxe7 Qxb2 loses material."},
                {"move_number": 17, "player": "B", "move": "cxb4", "commentary": ""},
                {"move_number": 18, "player": "W", "move": "Nb5", "commentary": ""},
                {"move_number": 18, "player": "B", "move": "Nxd5!", "commentary": ""},
                {"move_number": 19, "player": "W", "move": "Bf3", "commentary": ""},
                {"move_number": 19, "player": "B", "move": "Bd3!", "commentary": ""},
                {"move_number": 20, "player": "W", "move": "Bxd5", "commentary": ""},
                {"move_number": 20, "player": "B", "move": "Bxb5", "commentary": ""},
                {"move_number": 21, "player": "W", "move": "Bxa8", "commentary": ""},
                {"move_number": 21, "player": "B", "move": "Bxf1", "commentary": ""},
                {"move_number": 22, "player": "W", "move": "Be4", "commentary": ""},
                {"move_number": 22, "player": "B", "move": "Ba6", "commentary": "White resigns."}
            ]
        },
        "sidelines": [
            {
                "id": "game_68_sideline_7_dxc5",
                "name": "Alternative 7 dxc5",
                "description": "White plays 7 dxc5 leading to an early queen trade.",
                "startingMoveIndex": -1,
                "moves": [
                    {
                        "move_number": 7,
                        "player": "W",
                        "move": "dxc5",
                        "commentary": "After 7 dxc5 dxc5 8 Qxd8 Rxd8 White would have to play well to draw the endgame."
                    },
                    {"move_number": 7, "player": "B", "move": "dxc5", "commentary": ""},
                    {"move_number": 8, "player": "W", "move": "Qxd8", "commentary": ""},
                    {"move_number": 8, "player": "B", "move": "Rxd8", "commentary": ""}
                ]
            },
            {
                "id": "game_68_sideline_7_d5",
                "name": "Alternative 7 d5",
                "description": "White plays 7 d5 to close the center.",
                "startingMoveIndex": -1,
                "moves": [
                    {
                        "move_number": 7,
                        "player": "W",
                        "move": "d5",
                        "commentary": "Sometimes White blocks the centre with 7 d5 when 7...h6 8 Bh4 e5 would be standard play."
                    },
                    {"move_number": 7, "player": "B", "move": "h6", "commentary": ""},
                    {"move_number": 8, "player": "W", "move": "Bh4", "commentary": ""},
                    {"move_number": 8, "player": "B", "move": "e5", "commentary": ""}
                ]
            },
            {
                "id": "game_68_sideline_7_d5_qb6",
                "name": "Alternative 8...Qb6 in 7 d5 line",
                "description": "Black responds with 8...Qb6 after 7 d5.",
                "startingMoveIndex": -1,
                "moves": [
                    {"move_number": 7, "player": "W", "move": "d5", "commentary": ""},
                    {"move_number": 7, "player": "B", "move": "h6", "commentary": ""},
                    {"move_number": 8, "player": "W", "move": "Bh4", "commentary": ""},
                    {
                        "move_number": 8,
                        "player": "B",
                        "move": "Qb6",
                        "commentary": "Hoping to reach similar positions to the main line."
                    }
                ]
            },
            {
                "id": "game_68_sideline_9_ne4",
                "name": "Alternative 9...Ne4",
                "description": "Black tries the immediate 9...Ne4.",
                "startingMoveIndex": 3,
                "moves": [
                    {
                        "move_number": 9,
                        "player": "B",
                        "move": "Ne4",
                        "commentary": "The immediate 9...Ne4 is an interesting alternative."
                    }
                ]
            },
            {
                "id": "game_68_sideline_10_rc1",
                "name": "Alternative 10 Rc1",
                "description": "White plays the more logical 10 Rc1.",
                "startingMoveIndex": 5,
                "moves": [
                    {
                        "move_number": 10,
                        "player": "W",
                        "move": "Rc1",
                        "commentary": "10 Rc1 is more logical so that White can meet 10...Qb6 with 11 b3."
                    },
                    {"move_number": 10, "player": "B", "move": "Qb6", "commentary": ""},
                    {"move_number": 11, "player": "W", "move": "b3", "commentary": ""},
                    {
                        "move_number": 11,
                        "player": "B",
                        "move": "Rfe8",
                        "commentary": "In Law-Gallagher, British Championship 1997 Black had an attractive position."
                    },
                    {"move_number": 12, "player": "W", "move": "h3?!", "commentary": ""},
                    {"move_number": 12, "player": "B", "move": "g5!", "commentary": ""},
                    {"move_number": 13, "player": "W", "move": "Bg3", "commentary": ""},
                    {"move_number": 13, "player": "B", "move": "Ne4", "commentary": ""},
                    {"move_number": 14, "player": "W", "move": "Nxe4", "commentary": ""},
                    {"move_number": 14, "player": "B", "move": "Bxe4", "commentary": ""},
                    {"move_number": 15, "player": "W", "move": "dxc5", "commentary": ""},
                    {"move_number": 15, "player": "B", "move": "Nxc5", "commentary": ""},
                    {"move_number": 16, "player": "W", "move": "Nd4", "commentary": ""},
                    {"move_number": 16, "player": "B", "move": "Rad8", "commentary": ""}
                ]
            },
            {
                "id": "game_68_sideline_11_qd2",
                "name": "Alternative 11 Qd2",
                "description": "White tries 11 Qd2 to defend the b2-pawn.",
                "startingMoveIndex": 7,
                "moves": [
                    {
                        "move_number": 11,
                        "player": "W",
                        "move": "Qd2",
                        "commentary": "If 11 Qd2 g5 12 Bg3 Ne4 13 Nxe4 Bxe4 and Black seems to win a pawn."
                    },
                    {"move_number": 11, "player": "B", "move": "g5", "commentary": ""},
                    {"move_number": 12, "player": "W", "move": "Bg3", "commentary": ""},
                    {"move_number": 12, "player": "B", "move": "Ne4", "commentary": ""},
                    {"move_number": 13, "player": "W", "move": "Nxe4", "commentary": ""},
                    {"move_number": 13, "player": "B", "move": "Bxe4", "commentary": ""}
                ]
            },
            {
                "id": "game_68_sideline_11_qb3",
                "name": "Alternative 11 Qb3",
                "description": "White tries 11 Qb3 but Black also gets the advantage.",
                "startingMoveIndex": 7,
                "moves": [
                    {
                        "move_number": 11,
                        "player": "W",
                        "move": "Qb3",
                        "commentary": "If 11 Qb3 g5 12 Bg3 Ne4 13 Nxe4 Bxe4 14 Nd2 Bg6 and White seems to lose a pawn."
                    },
                    {"move_number": 11, "player": "B", "move": "g5", "commentary": ""},
                    {"move_number": 12, "player": "W", "move": "Bg3", "commentary": ""},
                    {"move_number": 12, "player": "B", "move": "Ne4", "commentary": ""},
                    {"move_number": 13, "player": "W", "move": "Nxe4", "commentary": ""},
                    {"move_number": 13, "player": "B", "move": "Bxe4", "commentary": ""},
                    {"move_number": 14, "player": "W", "move": "Nd2", "commentary": ""},
                    {"move_number": 14, "player": "B", "move": "Bg6", "commentary": ""}
                ]
            },
            {
                "id": "game_68_sideline_13_nxb6",
                "name": "Alternative 13 Nxb6",
                "description": "White captures on b6.",
                "startingMoveIndex": 11,
                "moves": [
                    {
                        "move_number": 13,
                        "player": "W",
                        "move": "Nxb6",
                        "commentary": "13 Nxb6 Qxb6 again leaves the b-pawn in difficulties."
                    },
                    {"move_number": 13, "player": "B", "move": "Qxb6", "commentary": ""}
                ]
            },
            {
                "id": "game_68_sideline_15_nxd5",
                "name": "Alternative 15 Nxd5",
                "description": "White plays 15 Nxd5 in the combination.",
                "startingMoveIndex": 15,
                "moves": [
                    {
                        "move_number": 15,
                        "player": "W",
                        "move": "Nxd5",
                        "commentary": "Or 15 Nxd5 Nxd5 16 Qxb4 Nxb4 17 Bxe7 Rfe8 18 Bxd6 Rad8 is winning for Black."
                    },
                    {"move_number": 15, "player": "B", "move": "Nxd5", "commentary": ""},
                    {"move_number": 16, "player": "W", "move": "Qxb4", "commentary": ""},
                    {"move_number": 16, "player": "B", "move": "Nxb4", "commentary": ""},
                    {"move_number": 17, "player": "W", "move": "Bxe7", "commentary": ""},
                    {"move_number": 17, "player": "B", "move": "Rfe8", "commentary": ""},
                    {"move_number": 18, "player": "W", "move": "Bxd6", "commentary": ""},
                    {"move_number": 18, "player": "B", "move": "Rad8", "commentary": ""}
                ]
            },
            {
                "id": "game_68_sideline_17_qxe7",
                "name": "Alternative 17 Qxe7",
                "description": "White tries 17 Qxe7.",
                "startingMoveIndex": 19,
                "moves": [
                    {
                        "move_number": 17,
                        "player": "W",
                        "move": "Qxe7",
                        "commentary": "17 Qxe7 Qxb2 loses material."
                    },
                    {"move_number": 17, "player": "B", "move": "Qxb2", "commentary": ""}
                ]
            }
        ]
    }
}

data["exercises"].append(ex1)
data["exercises"].append(ex2)
data["exercises"].append(ex3)

with open("/Users/lfesch/work_files/chess/parsed_pages_171_175.json", "w") as f:
    json.dump(data, f, indent=2)

print("JSON file created successfully.")
