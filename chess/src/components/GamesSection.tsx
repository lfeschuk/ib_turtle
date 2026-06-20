import React, { useState, useMemo, useRef, useEffect } from 'react';
import { 
  Play, 
  Pause, 
  Search, 
  Filter, 
  ChevronRight, 
  Trophy, 
  Calendar, 
  MapPin, 
  Compass,
  ArrowRight,
  RefreshCw,
  ChevronsLeft,
  ArrowLeft,
  ChevronsRight
} from 'lucide-react';
import { SampleBookPage, ParsedChessGame, ChessMove } from '../types';
import { ChessBoard } from './ChessBoard';

interface GamesSectionProps {
  currentBook: { title: string; exercises: SampleBookPage[] };
  selectedExerciseId: string;
  setSelectedExerciseId: (id: string) => void;
  activeExercise: SampleBookPage | null;
  activeGame: ParsedChessGame;
  currentMoveIndex: number;
  setCurrentMoveIndex: (idx: number) => void;
  gameMoves: ChessMove[];
  playbackSpeed: number;
  setPlaybackSpeed: (speed: number) => void;
  isPlaying: boolean;
  setIsPlaying: (val: boolean) => void;
}

export function getMilestoneBadges(item: SampleBookPage): string[] {
  const badges: string[] = [];
  const text = (item.textContext || '') + ' ' + (item.preparsedJson?.interactive_section?.moves?.map(m => m.commentary || '').join(' ') || '');
  const lowerText = text.toLowerCase();
  
  if (lowerText.includes('sacrifice') || lowerText.includes('sacr') || lowerText.includes('sacf')) {
    badges.push('Sacrifice');
  }
  if (lowerText.includes('endgame') || lowerText.includes('king walk') || lowerText.includes('pawn structure')) {
    badges.push('Endgame');
  }
  if (lowerText.includes('bishop') && lowerText.includes('knight')) {
    badges.push('Minor Duel');
  }
  if (lowerText.includes('blunder') || lowerText.includes('error') || lowerText.includes('?!') || lowerText.includes('??')) {
    badges.push('Blunder Check');
  }
  if (lowerText.includes('pin ') || lowerText.includes('pinned')) {
    badges.push('Tactical Pin');
  }
  if (lowerText.includes('mate') || lowerText.includes('mating') || lowerText.includes('checkmate')) {
    badges.push('Mating Net');
  }
  if (lowerText.includes('castle') || lowerText.includes('castling') || lowerText.includes('king safety')) {
    badges.push('King Safety');
  }

  // Ensure we always have at least one descriptive badge
  if (badges.length === 0) {
    badges.push('Theoretical');
  }

  return badges.slice(0, 3); // Max 3 badges
}

export const GamesSection: React.FC<GamesSectionProps> = ({
  currentBook,
  selectedExerciseId,
  setSelectedExerciseId,
  activeExercise,
  activeGame,
  currentMoveIndex,
  setCurrentMoveIndex,
  gameMoves,
  playbackSpeed,
  setPlaybackSpeed,
  isPlaying,
  setIsPlaying,
}) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedChapter, setSelectedChapter] = useState<string>('all');
  const [selectedYear, setSelectedYear] = useState<string>('all');
  const [selectedResult, setSelectedResult] = useState<string>('all'); // all, white, black, draw
  const movesContainerRef = useRef<HTMLDivElement>(null);

  // Filter games (exclude tactical exercises)
  const allGames = useMemo(() => {
    return currentBook.exercises.filter(ex => ex.id.startsWith('game_') && ex.id !== 'game_1_tactical_trap');
  }, [currentBook.exercises]);

  // Extract chapters, years, results list for dropdowns
  const chapters = useMemo(() => {
    const set = new Set<string>();
    allGames.forEach(g => {
      const match = g.description?.match(/Chapter\s+(\d+)/i);
      if (match) set.add(match[1]);
    });
    return Array.from(set).sort((a, b) => parseInt(a, 10) - parseInt(b, 10));
  }, [allGames]);

  const years = useMemo(() => {
    const set = new Set<string>();
    allGames.forEach(g => {
      const match = g.title.match(/\b(19\d{2}|20\d{2})\b/);
      if (match) set.add(match[1]);
    });
    return Array.from(set).sort();
  }, [allGames]);

  // Apply filters
  const filteredGames = useMemo(() => {
    return allGames.filter(g => {
      const titleLower = g.title.toLowerCase();
      const descLower = (g.description || '').toLowerCase();
      
      const matchesSearch = titleLower.includes(searchTerm.toLowerCase()) || descLower.includes(searchTerm.toLowerCase());
      
      let matchesChapter = true;
      if (selectedChapter !== 'all') {
        matchesChapter = (g.description || '').includes(`Chapter ${selectedChapter}`);
      }

      let matchesYear = true;
      if (selectedYear !== 'all') {
        matchesYear = g.title.includes(selectedYear);
      }

      let matchesResult = true;
      if (selectedResult !== 'all') {
        // Results are typically white win, black win, or draw.
        // We look up the text in description or textContext if it lists the winner
        const commentaryLower = (g.textContext || '').toLowerCase();
        if (selectedResult === 'white') {
          matchesResult = titleLower.includes('1-0') || commentaryLower.includes('white wins') || titleLower.includes('salgado') || titleLower.includes('portisch') || titleLower.includes('kamsky');
        } else if (selectedResult === 'black') {
          matchesResult = titleLower.includes('0-1') || commentaryLower.includes('black wins') || titleLower.includes('gallagher') || titleLower.includes('bologan') || titleLower.includes('shirov');
        } else if (selectedResult === 'draw') {
          matchesResult = titleLower.includes('1/2') || titleLower.includes('draw');
        }
      }

      return matchesSearch && matchesChapter && matchesYear && matchesResult;
    });
  }, [allGames, searchTerm, selectedChapter, selectedYear, selectedResult]);

  // Scroll active move into view inside PGNDecoder movelist index
  useEffect(() => {
    if (movesContainerRef.current && currentMoveIndex >= 0) {
      const activeEl = movesContainerRef.current.querySelector(`#game-move-${currentMoveIndex}`);
      if (activeEl) {
        activeEl.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
      }
    }
  }, [currentMoveIndex]);

  return (
    <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 w-full">
      {/* LEFT COLUMN: Chessboard & Playback HUD */}
      <div className="lg:col-span-5 flex flex-col gap-6">
        <div className="bg-[#FAF8F5] border border-black/10 rounded-2xl p-6 shadow-sm text-left">
          <div className="flex justify-between items-start gap-4 mb-4 border-b border-black/5 pb-3">
            <div>
              <span className="text-[10px] font-sans font-bold uppercase tracking-widest text-[#D97706] block mb-1">
                GAMES PLAYER
              </span>
              <h2 className="text-2xl font-serif font-medium leading-tight text-[#1A1A1A]">
                {activeGame.white || 'White'} vs {activeGame.black || 'Black'}
              </h2>
              <div className="text-[11px] font-sans uppercase tracking-wider opacity-60 mt-1 flex items-center gap-3">
                <span className="flex items-center gap-1"><MapPin size={12} className="opacity-60" /> {activeGame.event || 'Grandmaster Duel'}</span>
              </div>
            </div>
            
            {activeExercise && (
              <div className="flex flex-wrap gap-1 items-end justify-end max-w-[150px]">
                {getMilestoneBadges(activeExercise).map((badge, i) => (
                  <span 
                    key={i} 
                    className={`text-[8.5px] font-sans font-bold uppercase tracking-wider px-2 py-0.5 rounded shadow-3xs ${
                      badge === 'Sacrifice' ? 'bg-amber-100 text-amber-900 border border-amber-300/40' :
                      badge === 'Endgame' ? 'bg-blue-100 text-blue-900 border border-blue-300/40' :
                      badge === 'Minor Duel' ? 'bg-emerald-100 text-emerald-900 border border-emerald-300/40' :
                      badge === 'Blunder Check' ? 'bg-red-100 text-red-900 border border-red-300/40' :
                      badge === 'Tactical Pin' ? 'bg-purple-100 text-purple-900 border border-purple-300/40' :
                      badge === 'Mating Net' ? 'bg-rose-100 text-rose-900 border border-rose-300/40' :
                      'bg-stone-100 text-stone-700 border border-stone-300/40'
                    }`}
                  >
                    {badge}
                  </span>
                ))}
              </div>
            )}
          </div>

          {/* Active Commentary */}
          <div className="p-4 bg-white border border-black/10 rounded-xl font-serif italic text-sm text-stone-800 leading-relaxed mb-6 text-left">
            "{currentMoveIndex >= 0 
              ? gameMoves[currentMoveIndex]?.commentary || "No specific comments for this move position."
              : activeGame.initial_moves 
                ? "Precursor opening line completed. Use the navigation buttons below or autoplay to watch the illustrative game unfold."
                : "No game moves loaded. Use the games directory to load a game."
            }"
          </div>

          {/* Chessboard Component Wrapper */}
          <div className="w-full flex justify-center py-4 bg-white/40 border border-black/5 rounded-xl mb-6 shadow-2xs">
            <ChessBoard
              key={`game_${selectedExerciseId}`}
              initialMoves={activeGame.initial_moves || ""}
              gameMoves={gameMoves}
              currentMoveIndex={currentMoveIndex}
              onMoveSelected={(idx) => {
                setIsPlaying(false);
                setCurrentMoveIndex(Math.max(-1, Math.min(gameMoves.length - 1, idx)));
              }}
            />
          </div>

          {/* Autoplay & Pace settings */}
          <div className="pt-4 border-t border-black/10 flex flex-wrap items-center justify-between gap-4 text-stone-600">
            <div className="flex items-center gap-1.5">
              <button
                onClick={() => setIsPlaying(!isPlaying)}
                disabled={gameMoves.length === 0}
                className={`flex items-center gap-1 px-4 py-1.5 rounded uppercase text-[9px] font-bold transition-all border font-sans ${
                  isPlaying 
                    ? 'bg-amber-800 text-white border-amber-800 hover:bg-amber-900' 
                    : 'bg-[#1A1A1A] text-white border-[#1A1A1A] hover:bg-black'
                }`}
              >
                {isPlaying ? <Pause size={10} /> : <Play size={10} />}
                <span>{isPlaying ? 'Pause' : 'Auto Play'}</span>
              </button>
            </div>
            
            <div className="flex items-center gap-2">
              <span className="text-[9px] font-mono uppercase tracking-widest opacity-50 font-bold">Pacing:</span>
              <input
                type="range"
                min="1000"
                max="5000"
                step="500"
                value={playbackSpeed}
                onChange={(e) => setPlaybackSpeed(Number(e.target.value))}
                className="w-20 accent-[#D97706] h-1 bg-black/10 rounded cursor-pointer"
              />
              <span className="text-[10px] font-mono text-[#1A1A1A]/70">{(playbackSpeed / 1000).toFixed(1)}s</span>
            </div>
          </div>
        </div>
      </div>

      {/* RIGHT COLUMN: Games directory search/filter & Move timeline */}
      <div className="lg:col-span-7 flex flex-col gap-6 text-left">
        {/* Game Directory Dashboard */}
        <div className="bg-[#141414] text-white border border-white/5 rounded-2xl p-6 shadow-md flex flex-col min-h-[300px]">
          <div className="flex justify-between items-center mb-4">
            <div>
              <span className="text-[10px] font-mono uppercase tracking-widest opacity-40 block mb-1">
                GAMES ARCHIVE
              </span>
              <h3 className="text-xl font-serif text-white font-light tracking-tight">
                Illustrative Volume ({allGames.length} Total Games)
              </h3>
            </div>
          </div>

          {/* Filters Area */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-2 mb-4 bg-black/30 p-2.5 rounded-xl border border-white/5">
            {/* Search Input */}
            <div className="relative md:col-span-1">
              <Search className="absolute left-2.5 top-2.5 h-3.5 w-3.5 text-gray-500" />
              <input
                type="text"
                placeholder="Search players..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full bg-white/5 border border-white/10 rounded-lg py-1.5 pl-8 pr-3 text-xs text-white placeholder-gray-500 focus:outline-none focus:border-amber-500"
              />
            </div>

            {/* Chapter Select */}
            <div className="relative">
              <select
                value={selectedChapter}
                onChange={(e) => setSelectedChapter(e.target.value)}
                className="w-full bg-white/5 border border-white/10 rounded-lg py-1.5 px-3 text-xs text-stone-300 focus:outline-none focus:border-amber-500 cursor-pointer"
              >
                <option value="all" className="bg-[#141414] text-white">All Chapters</option>
                {chapters.map(c => (
                  <option key={c} value={c} className="bg-[#141414] text-white">Chapter {c}</option>
                ))}
              </select>
            </div>

            {/* Year Select */}
            <div className="relative">
              <select
                value={selectedYear}
                onChange={(e) => setSelectedYear(e.target.value)}
                className="w-full bg-white/5 border border-white/10 rounded-lg py-1.5 px-3 text-xs text-stone-300 focus:outline-none focus:border-amber-500 cursor-pointer"
              >
                <option value="all" className="bg-[#141414] text-white">All Years</option>
                {years.map(y => (
                  <option key={y} value={y} className="bg-[#141414] text-white">{y}</option>
                ))}
              </select>
            </div>

            {/* Result Filter */}
            <div className="relative">
              <select
                value={selectedResult}
                onChange={(e) => setSelectedResult(e.target.value)}
                className="w-full bg-white/5 border border-white/10 rounded-lg py-1.5 px-3 text-xs text-stone-300 focus:outline-none focus:border-amber-500 cursor-pointer"
              >
                <option value="all" className="bg-[#141414] text-white">All Results</option>
                <option value="white" className="bg-[#141414] text-white">White Wins</option>
                <option value="black" className="bg-[#141414] text-white">Black Wins</option>
                <option value="draw" className="bg-[#141414] text-white">Draws</option>
              </select>
            </div>
          </div>

          {/* Filtered games list */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-2.5 max-h-[220px] overflow-y-auto pr-1">
            {filteredGames.length > 0 ? (
              filteredGames.map((g) => {
                const isActive = g.id === selectedExerciseId;
                const badges = getMilestoneBadges(g);
                return (
                  <div
                    key={g.id}
                    onClick={() => setSelectedExerciseId(g.id)}
                    className={`p-3 rounded-xl border text-left cursor-pointer transition-all ${
                      isActive
                        ? 'bg-white/10 border-white text-white font-bold'
                        : 'bg-white/5 border-white/5 text-gray-400 hover:text-white hover:bg-white/10'
                    }`}
                  >
                    <div className="text-[11.5px] font-sans leading-tight line-clamp-1 flex items-center justify-between gap-2">
                      <span className={isActive ? 'text-white' : 'text-stone-300'}>{g.title}</span>
                      <ChevronRight size={10} className="opacity-40" />
                    </div>
                    <div className="text-[9.5px] font-serif italic mt-1 opacity-60 line-clamp-1">{g.description}</div>
                    <div className="flex gap-1 mt-2">
                      {badges.map((b, i) => (
                        <span key={i} className="text-[8px] font-sans px-1.5 py-0.5 rounded bg-white/5 border border-white/5 text-white/55">
                          {b}
                        </span>
                      ))}
                    </div>
                  </div>
                );
              })
            ) : (
              <div className="p-8 border border-dashed border-white/10 rounded-xl col-span-2 text-center text-xs text-gray-500 italic font-sans leading-relaxed">
                No games match your search filters. Try resetting terms!
              </div>
            )}
          </div>
        </div>

        {/* Scrollable PGN Style Move List */}
        <div className="bg-[#141414] text-white border border-white/5 rounded-2xl p-6 shadow-md flex-grow">
          <span className="text-[10px] font-mono uppercase tracking-widest opacity-40 block mb-2">
            MOVE CHRONOLOGY INDEX
          </span>
          <h3 className="text-lg font-serif text-white font-light tracking-tight mb-4">
            PGNDecoder Move Logger ({gameMoves.length} Moves)
          </h3>

          <div 
            ref={movesContainerRef}
            className="space-y-1 bg-black/40 border border-white/5 p-3 rounded-xl max-h-[300px] overflow-y-auto"
          >
            {gameMoves.length === 0 ? (
              <div className="p-8 text-center text-gray-500 italic text-xs font-sans">
                No moves available for this game.
              </div>
            ) : (
              gameMoves.map((m, index) => {
                const isActive = currentMoveIndex === index;
                return (
                  <div
                    key={index}
                    id={`game-move-${index}`}
                    onClick={() => setCurrentMoveIndex(index)}
                    className={`flex items-baseline justify-between p-2.5 cursor-pointer rounded transition-all ${
                      isActive
                        ? 'bg-white/10 text-white border-l-2 border-[#D97706]'
                        : 'hover:bg-white/5 text-gray-400 hover:text-gray-200'
                    }`}
                  >
                    <div className="flex items-baseline gap-3 min-w-0 flex-1">
                      <span className="w-8 text-[11px] text-gray-600 text-right shrink-0 font-mono">
                        {m.move_number}{m.player === 'W' ? '.' : '...'}
                      </span>
                      <span className={`px-1.5 py-0.5 rounded text-xs font-bold shrink-0 ${
                        isActive ? 'text-amber-300 bg-amber-950/40' : 'text-blue-300 bg-blue-950/20'
                      }`}>
                        {m.move}
                      </span>
                      <span className="text-xs text-gray-400 truncate max-w-[280px] md:max-w-[400px]">
                        {m.commentary}
                      </span>
                    </div>
                    <ChevronRight size={10} className={isActive ? 'text-amber-400' : 'opacity-10'} />
                  </div>
                );
              })
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
