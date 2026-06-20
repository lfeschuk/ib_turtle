import chess

def test_moves(moves_str):
    board = chess.Board()
    moves = moves_str.split()
    for i, m in enumerate(moves):
        # Skip numbers
        if i % 3 == 0:
            continue
        try:
            board.push_san(m)
        except Exception as e:
            return False, f"Failed at move {m}: {e}"
    return True, board.fen()

# Main line of Game 34 up to 9...e5
base_moves = "1. d4 Nf6 2. c4 g6 3. Nc3 Bg7 4. e4 d6 5. f3 O-O 6. Be3 Nc6 7. Qd2 a6 8. Nge2 Rb8 9. Nc1 e5"

# Let's test candidate sidelines starting from move 10 (White's move)
# Candidate 1: 10. Nb3 exd4 11. Nxd4 Nxd4 12. Bxd4 c5
cand1 = base_moves + " 10. Nb3 exd4 11. Nxd4 Nxd4 12. Bxd4 c5"
ok, res = test_moves(cand1)
print("Candidate 1 (10. Nb3 exd4 11. Nxd4 Nxd4 12. Bxd4 c5):", ok, res)

# Candidate 2: 10. Nb3 exd4 11. Nxd5 Nc5 (the literal OCR representation we had doubts about)
cand2 = base_moves + " 10. Nb3 exd4 11. Nxd5 Nc5"
ok, res = test_moves(cand2)
print("Candidate 2 (10. Nb3 exd4 11. Nxd5 Nc5):", ok, res)

# Candidate 3: 10. Nb3 exd4 11. Nxd4 Ne5
cand3 = base_moves + " 10. Nb3 exd4 11. Nxd4 Ne5"
ok, res = test_moves(cand3)
print("Candidate 3 (10. Nb3 exd4 11. Nxd4 Ne5):", ok, res)

# Candidate 4: 10. Nb3 exd4 11. Nxd4 Bd7
cand4 = base_moves + " 10. Nb3 exd4 11. Nxd4 Bd7"
ok, res = test_moves(cand4)
print("Candidate 4 (10. Nb3 exd4 11. Nxd4 Bd7):", ok, res)
