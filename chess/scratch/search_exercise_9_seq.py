from chess import Board, Move

def try_sequence(moves_list):
    board = Board()
    for m in moves_list:
        try:
            board.push_san(m)
        except:
            return None
    return board

# We want to find a sequence:
# 1. d4 Nf6 2. c4 g6 3. Nc3 Bg7 4. e4 d6 5. Nf3 O-O 6. Be2 e5 7. O-O Nbd7 8. Be3 Re8 9. d5 Nc5
# Now we need to get Knight off f3 and Queen to a good square.
# Let's try:
# 10. Nd2 a6 (Black plays a6 instead of a5)
# 11. Qc2 (White plays Qc2, f3 is empty, Queen on c2)
# Now Black plays something neutral, say 11...Rb8
# And White plays 12. b4
# Then Black plays 12...Ncxe4 13. Nxe4 Nxe4 14. Qxe4 Bf5 15. Qf3 e4
# Let's check if this works.

seq = [
    'd4', 'Nf6', 'c4', 'g6', 'Nc3', 'Bg7', 'e4', 'd6', 'Nf3', 'O-O',
    'Be2', 'e5', 'O-O', 'Nbd7', 'Be3', 'Re8', 'd5', 'Nc5',
    'Nd2', 'a6',
    'Qc2', 'Rb8',
    'b4', 'Ncxe4', 'Nd2xe4', 'Nxe4', 'Qxe4', 'Bf5', 'Qf3', 'e4'
]

board = try_sequence(seq)
if board:
    print("SUCCESS!")
    print(board)
else:
    print("FAILED")

    # Let's debug where it failed
    board = Board()
    for i, m in enumerate(seq):
        try:
            board.push_san(m)
            print(f"{i+1}: {m} OK")
        except Exception as e:
            print(f"{i+1}: {m} FAILED: {e}")
            break
