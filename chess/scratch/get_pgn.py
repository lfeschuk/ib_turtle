import urllib.request
import re
import sys

# Search google for the game
query = "Ioseliani vs Gallagher Biel 1990 chessgames"
url = f"https://www.google.com/search?q={urllib.parse.quote(query)}"
req = urllib.request.Request(
    url, 
    headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
)

try:
    with urllib.request.urlopen(req) as response:
        html = response.read().decode('utf-8')
        # Find chessgames.com/perl/chessgame?gid=...
        gids = re.findall(r'chessgames\.com/perl/chessgame\?gid=(\d+)', html)
        if gids:
            print(f"Found GIDs: {gids}")
            gid = gids[0]
            game_url = f"https://www.chessgames.com/perl/chessgame?gid={gid}"
            print(f"Fetching game from: {game_url}")
            game_req = urllib.request.Request(
                game_url,
                headers={'User-Agent': 'Mozilla/5.0'}
            )
            with urllib.request.urlopen(game_req) as game_resp:
                game_html = game_resp.read().decode('utf-8')
                # Extract PGN or moves
                # In chessgames.com, the moves are often in a JS variable or in a specific div
                # Let's just print the text around "pgn" or search for the moves list
                moves_match = re.search(r'gMoves\s*=\s*\[([^\]]+)\]', game_html)
                if moves_match:
                    print("Found moves in JS:")
                    print(moves_match.group(1))
                else:
                    # Let's save the HTML to see it
                    with open('scratch/game.html', 'w', encoding='utf-8') as f:
                        f.write(game_html)
                    print("Saved HTML to scratch/game.html")
        else:
            print("No chessgames.com links found.")
            with open('scratch/search_results.html', 'w', encoding='utf-8') as f:
                f.write(html)
            print("Saved search results to scratch/search_results.html")
except Exception as e:
    print(f"Error: {e}")
