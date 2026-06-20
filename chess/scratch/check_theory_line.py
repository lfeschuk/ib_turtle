import chess

board = chess.Board()

moves = [
    "d4", "Nf6", "c4", "g6", "Nc3", "Bg7", "e4", "d6", "f4", "O-O",
    "Nf3", "Na6", "Bd3", "e5", "dxe5", "dxe5", "Nxe5", "Nc5",
    "Be2", "Qxd1+", "Kxd1", "Rd8+", "Kc2", "Nfxe4", "Nxe4", "Bf5",
    "Re1", "Bxe5", "fxe5", "Rd4", "Kc3", "Rd3+", "Kc2", "Rd4",
    "Kc3", "Rd3+", "Kb4", "Na6+", "Ka5", "b6+", "Kxa6", "Bc8+",
    "Kb5", "Bd7+", "Ka6", "Bc8+", "Kb5", "Bd7+"
]

for i, move in enumerate(moves):
    try:
        # chess.Board.push_san expects standard SAN.
        # We need to make sure we handle check suffix (+)
        board.push_san(move)
        print(f"{i+1}. {move} ok. FEN: {board.fen()}")
    except Exception as e:
        print(f"Error at move {i+1} ({move}): {e}")
        print(board)
        break
