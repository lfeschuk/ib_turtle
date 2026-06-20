import urllib.request
import re
import sys

# Search DuckDuckGo html
query = "Ioseliani Gallagher 1990"
url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(query)}"
req = urllib.request.Request(
    url, 
    headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
)

try:
    with urllib.request.urlopen(req) as response:
        html = response.read().decode('utf-8')
        gids = re.findall(r'chessgames\.com/perl/chessgame\?gid=(\d+)', html)
        # Print all links that look like external links
        all_links = re.findall(r'href="([^"]+)"', html)
        for link in all_links:
            if 'chess' in link or 'pgn' in link or 'games' in link:
                print("Found link:", link)
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
                moves_match = re.search(r'gMoves\s*=\s*\[([^\]]+)\]', game_html)
                if moves_match:
                    print("Found moves in JS:")
                    print(moves_match.group(1))
                else:
                    # Look for PGN download link or text
                    pgn_match = re.search(r'href="(/pgn/[^"]+)"', game_html)
                    if pgn_match:
                        pgn_url = "https://www.chessgames.com" + pgn_match.group(1)
                        print(f"Fetching PGN from: {pgn_url}")
                        pgn_req = urllib.request.Request(pgn_url, headers={'User-Agent': 'Mozilla/5.0'})
                        with urllib.request.urlopen(pgn_req) as pgn_resp:
                            print(pgn_resp.read().decode('utf-8'))
                    else:
                        with open('scratch/game.html', 'w', encoding='utf-8') as f:
                            f.write(game_html)
                        print("Saved HTML to scratch/game.html")
        else:
            print("No chessgames.com links found on DuckDuckGo.")
            with open('scratch/ddg_search.html', 'w', encoding='utf-8') as f:
                f.write(html)
            print("Saved DDG search results to scratch/ddg_search.html")
except Exception as e:
    print(f"Error: {e}")
