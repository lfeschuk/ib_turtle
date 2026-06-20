import chess

game = chess.Board()

# 1 Nf3 Nf6 2 c4 g6 3 d4 Bg7 4 Nc3 0-0 5 g3 d6 6 Bg2 Nbd7 7 0-0 e5 8 e4 c6 9 h3 Qb6
moves = [
    "Nf3", "Nf6", "c4", "g6", "d4", "Bg7", "Nc3", "O-O", "g3", "d6", 
    "Bg2", "Nbd7", "O-O", "e5", "e4", "c6", "h3", "Qb6"
]

for move in moves:
    game.push_san(move)

print("Position after 9...Qb6:")
print(game)

# 10 c5!? dxc5 11 dxe5 Ne8 12 e6!? fxe6 13 Ng5
next_moves = ["c5", "dxc5", "dxe5", "Ne8", "e6", "fxe6", "Ng5"]
for move in next_moves:
    game.push_san(move)

print("\nPosition after 13 Ng5:")
print(game)

# Now we suspect 13...Ne5
game.push_san("Ne5")

# 14 f4 Nf7
game.push_san("f4")
game.push_san("Nf7")

# 15 Nxf7 Bd4+! 16 Kh2 Rxf7 17 e5 Nc7 18 Ne4 Nd5 19 h4!
more_moves = ["Nxf7", "Bd4+", "Kh2", "Rxf7", "e5", "Nc7", "Ne4", "Nd5", "h4"]
for move in more_moves:
    game.push_san(move)

print("\nPosition after 19 h4:")
print(game)

# 19..Qd8 20 h5 Rg7 21 Ng5 gxh5? 22 Qxh5 Qe7 23 Be4 Bd7 24 Qh3
moves_24 = ["Qd8", "h5", "Rg7", "Ng5", "gxh5", "Qxh5", "Qe7", "Be4", "Bd7", "Qh3"]
for move in moves_24:
    game.push_san(move)

print("\nPosition after 24 Qh3:")
print(game)

# 24...c4 25 Rb1 b5 26 Kg2!
moves_26 = ["c4", "Rb1", "b5", "Kg2"]
for move in moves_26:
    game.push_san(move)

print("\nPosition after 26 Kg2:")
print(game)

# Now we need to figure out 26...??? 27 f5!
# Let's see what moves are legal for Black here.
# If Black plays 26...c5 (is it legal? Yes, if c7 pawn is still there?
# Wait, did Black have a pawn on c7?
# Initial moves: 8...c6. 10 c5 dxc5.
# So c6 was played. The d6 pawn took on c5.
# So Black has pawns on c7 and c5?
# Wait, if 8...c6, the pawn is on c6.
# 10 c5. Black plays dxc5. The d6 pawn takes c5.
# So Black has pawns on c6 and c5? No, d6 took c5, so d6 is gone, pawn is on c5.
# The c6 pawn is still on c6.
# If so, c6 pawn can move to c5 if c5 is empty? But c5 has a pawn.
# Wait, did we play c5 earlier?
# Ah, 17...Nc7 18 Ne4 Nd5.
# If Black plays 26...c5. If c6 pawn was still there, it can't move to c5 because c5 is occupied?
# Wait, did the c5 pawn move?
# Ah, 24...c4?
# If the pawn on c5 moved to c4.
# Then c6 pawn is free to move to c5!
# Yes! 24...c4 moved the pawn from c5 to c4.
# So now c5 is empty, and the c6 pawn can move to c5.
# So 26...c5 is legal!

# Let's try to push 26...c5
game.push_san("c5")
print("\nPosition after 26...c5:")
print(game)

# 27 f5!
game.push_san("f5")
print("\nPosition after 27 f5:")
print(game)

# Now White plays 27 f5.
# Black's response: OCR says "Bxeb" (maybe Bxe6 or Bxf5?)
# Let's see what is legal.
print("\nLegal moves for Black after 27 f5:")
for move in game.legal_moves:
    san = game.san(move)
    if san.startswith("B") or san.startswith("e"):
        print(san)
