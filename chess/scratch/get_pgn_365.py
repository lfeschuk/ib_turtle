import urllib.request
import re

url = "https://www.365chess.com/search_result.php?search=1&wplayer=Ioseliani&bplayer=Gallagher"
req = urllib.request.Request(
    url, 
    headers={'User-Agent': 'Mozilla/5.0'}
)

try:
    with urllib.request.urlopen(req) as response:
        html = response.read().decode('utf-8')
        # Look for links to games
        # Format: <a href="game.php?gid=...">
        games = re.findall(r'href="(game\.php\?gid=\d+)"', html)
        print("Found games:", games)
        for game in games[:3]:
            game_url = f"https://www.365chess.com/{game}"
            print(f"Fetching: {game_url}")
            game_req = urllib.request.Request(game_url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(game_req) as game_resp:
                game_html = game_resp.read().decode('latin-1') # Sometimes they use latin-1
                # Find PGN or moves
                # Look for PGN display
                pgn_match = re.search(r'<div class="pgn">(.*?)</div>', game_html, re.DOTALL)
                if pgn_match:
                    print("Found PGN:")
                    print(pgn_match.group(1))
                else:
                    # Just print some text around the game info
                    print("No PGN div found. Saving HTML.")
                    with open('scratch/game_365.html', 'w', encoding='utf-8') as f:
                        f.write(game_html)
except Exception as e:
    print(f"Error: {e}")
