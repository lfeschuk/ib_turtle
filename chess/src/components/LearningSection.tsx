import React, { useState, useMemo } from 'react';
import { 
  BookOpen, 
  ChevronRight, 
  ChevronDown, 
  Play, 
  Pause, 
  Sparkles,
  Volume2,
  VolumeX,
  RotateCcw
} from 'lucide-react';
import { SampleBookPage, ParsedChessGame, ChessMove, SidelineVariation } from '../types';
import { ChessBoard } from './ChessBoard';

// Grouping helper
interface ChapterGroup {
  chapterNumber: number;
  chapterTitle: string;
  items: SampleBookPage[];
}

function groupItemsByChapter(items: SampleBookPage[]): ChapterGroup[] {
  const groups: Record<string, ChapterGroup> = {};
  
  items.forEach(item => {
    const match = item.description?.match(/Chapter\s+(\d+)\s*\(([^)]+)\)/i);
    let chNum = 99;
    let chTitle = "General & Tactics";
    
    if (match) {
      chNum = parseInt(match[1], 10);
      chTitle = match[2].trim();
    }
    
    const key = `${chNum}_${chTitle}`;
    if (!groups[key]) {
      groups[key] = {
        chapterNumber: chNum,
        chapterTitle: chTitle,
        items: []
      };
    }
    groups[key].items.push(item);
  });
  
  return Object.values(groups).sort((a, b) => a.chapterNumber - b.chapterNumber);
}

interface LearningSectionProps {
  currentBook: { title: string; exercises: SampleBookPage[] };
  selectedExerciseId: string;
  setSelectedExerciseId: (id: string) => void;
  activeExercise: SampleBookPage | null;
  activeGame: ParsedChessGame;
  setActiveGame: (game: ParsedChessGame) => void;
  currentMoveIndex: number;
  setCurrentMoveIndex: (idx: number) => void;
  isExploringOpening: boolean;
  setIsExploringOpening: (val: boolean) => void;
  currentOpeningMoveIndex: number;
  setCurrentOpeningMoveIndex: (idx: number) => void;
  activeSideline: SidelineVariation | null;
  setActiveSideline: (sideline: SidelineVariation | null) => void;
  activeSidelineMoveIndex: number;
  setActiveSidelineMoveIndex: (idx: number) => void;
  openingMoves: ChessMove[];
  gameMoves: ChessMove[];
  getSidelinePrefixInitialMoves: (sideline: SidelineVariation) => string;
  enableSpeech: boolean;
  setEnableSpeech: (val: boolean) => void;
  playbackSpeed: number;
  setPlaybackSpeed: (speed: number) => void;
  isPlaying: boolean;
  setIsPlaying: (val: boolean) => void;
}

export const LearningSection: React.FC<LearningSectionProps> = ({
  currentBook,
  selectedExerciseId,
  setSelectedExerciseId,
  activeExercise,
  activeGame,
  currentMoveIndex,
  setCurrentMoveIndex,
  isExploringOpening,
  setIsExploringOpening,
  currentOpeningMoveIndex,
  setCurrentOpeningMoveIndex,
  activeSideline,
  setActiveSideline,
  activeSidelineMoveIndex,
  setActiveSidelineMoveIndex,
  openingMoves,
  gameMoves,
  getSidelinePrefixInitialMoves,
  enableSpeech,
  setEnableSpeech,
  playbackSpeed,
  setPlaybackSpeed,
  isPlaying,
  setIsPlaying,
}) => {
  // Chapter accordion state (keep active chapter open)
  const [openChapters, setOpenChapters] = useState<Record<string, boolean>>({ "1": true });

  const chapterGroups = useMemo(() => {
    // Only display study exercises/games in Learning section
    return groupItemsByChapter(currentBook.exercises);
  }, [currentBook.exercises]);

  const toggleChapter = (chapterNum: number) => {
    setOpenChapters(prev => ({
      ...prev,
      [chapterNum]: !prev[chapterNum]
    }));
  };

  const handleSidelineClick = (sld: SidelineVariation) => {
    setIsPlaying(false);
    setActiveSideline(sld);
    setActiveSidelineMoveIndex(-1);
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 w-full">
      {/* LEFT COLUMN: Chessboard, Commentary, Interactive Walkthrough Controls */}
      <div className="lg:col-span-5 flex flex-col gap-6">
        <div className="bg-[#FAF8F5] border border-black/10 rounded-2xl p-6 shadow-sm text-left">
          <div className="flex justify-between items-start gap-4 mb-4 border-b border-black/5 pb-3">
            <div>
              <span className="text-[10px] font-sans font-bold uppercase tracking-widest text-[#D97706] block mb-1">
                STUDY CORRIDOR
              </span>
              <h2 className="text-2xl font-serif font-medium leading-tight text-[#1A1A1A]">
                {activeGame.white || 'White'} vs {activeGame.black || 'Black'}
              </h2>
              <div className="text-[11px] font-sans uppercase tracking-wider opacity-60 mt-1">
                {activeGame.event || 'Opening Walkthrough'}
              </div>
            </div>
            
            <button
              onClick={() => setEnableSpeech(!enableSpeech)}
              className={`p-2 rounded-full border transition-all ${
                enableSpeech 
                  ? 'bg-amber-100 border-[#D97706]/35 text-[#D97706]' 
                  : 'bg-white border-black/10 text-gray-500 hover:text-black hover:border-black/35'
              }`}
              title="Toggle Voice Synthesizer Output"
            >
              {enableSpeech ? <Volume2 size={16} /> : <VolumeX size={16} />}
            </button>
          </div>

          {/* Active Commentary Text */}
          <div className="p-4 bg-amber-50/30 border-l-4 border-[#D97706] rounded-r-lg font-serif italic text-sm text-stone-900 leading-relaxed mb-6">
            "{activeSideline 
              ? (activeSidelineMoveIndex >= 0 
                ? activeSideline.moves[activeSidelineMoveIndex]?.commentary || "Alternative variation line move."
                : activeSideline.description || "Exploring sideline deviation.")
              : isExploringOpening
                ? (currentOpeningMoveIndex >= 0
                  ? openingMoves[currentOpeningMoveIndex]?.commentary || "No specific comments for this opening move."
                  : "Opening Explainer active! Click on the moves line in the explorer timeline, or click 'Autoplay' to inspect why both White and Black played these startup moves.")
                : (currentMoveIndex >= 0 
                  ? gameMoves[currentMoveIndex]?.commentary || "No commentary or tactical notations written for this move position."
                  : activeGame.initial_moves 
                    ? "Precursor opening line registered. Use the navigation buttons or autoplay to initiate commentary parsing."
                    : "No game moves loaded. Go to the Digitizer panel to initiate document extraction."
                )
            }"
          </div>

          {/* Chessboard Component Wrapper */}
          <div className="w-full flex justify-center py-4 bg-white/40 border border-black/5 rounded-xl mb-6 shadow-2xs">
            <ChessBoard
              key={`study_${selectedExerciseId}_${activeSideline?.id || ''}_${isExploringOpening}`}
              initialMoves={activeSideline ? getSidelinePrefixInitialMoves(activeSideline) : ""}
              gameMoves={activeSideline ? activeSideline.moves : (isExploringOpening ? openingMoves : gameMoves)}
              currentMoveIndex={activeSideline ? activeSidelineMoveIndex : (isExploringOpening ? currentOpeningMoveIndex : currentMoveIndex)}
              activeSideline={activeSideline}
              onMoveSelected={(idx) => {
                setIsPlaying(false);
                if (activeSideline) {
                  setActiveSidelineMoveIndex(Math.max(-1, Math.min(activeSideline.moves.length - 1, idx)));
                } else if (isExploringOpening) {
                  setCurrentOpeningMoveIndex(Math.max(-1, Math.min(openingMoves.length - 1, idx)));
                } else {
                  setCurrentMoveIndex(Math.max(-1, Math.min(gameMoves.length - 1, idx)));
                }
              }}
              sidelines={activeGame.sidelines}
              onAlternateSidelinePlayed={handleSidelineClick}
            />
          </div>

          {/* Sideline Selection Overlay when Divergence Point is Hit */}
          {activeGame.sidelines && activeGame.sidelines.length > 0 && (
            <div className="bg-amber-900/5 border border-amber-900/15 rounded-xl p-4 text-left">
              <span className="text-[10px] font-mono tracking-widest text-[#D97706] uppercase font-bold">
                ✦ Sideline Side-quests & Variations
              </span>
              
              {activeSideline ? (
                <div className="mt-3 space-y-3">
                  <div className="p-3 bg-white border border-amber-900/10 rounded-lg">
                    <span className="font-serif font-bold text-xs text-amber-900 block">{activeSideline.name}</span>
                    <p className="text-[11px] text-stone-600 font-serif mt-1">{activeSideline.description}</p>
                  </div>
                  <button
                    onClick={() => {
                      setActiveSideline(null);
                      setActiveSidelineMoveIndex(-1);
                    }}
                    className="w-full py-1.5 bg-amber-900 hover:bg-amber-950 text-white text-[10px] uppercase font-sans tracking-wider font-bold transition-all rounded shadow-xs"
                  >
                    ↩ Return to Main Game Corridor
                  </button>
                </div>
              ) : (
                <div className="mt-3 space-y-2">
                  <p className="text-[11px] text-stone-600 leading-normal font-serif">
                    Select a diverging sideline from the current board state:
                  </p>
                  {activeGame.sidelines.map((sld) => {
                    const isDivergedHere = sld.startingMoveIndex === currentMoveIndex;
                    return (
                      <div 
                        key={sld.id}
                        className={`p-3 rounded-lg border transition-all flex justify-between items-center gap-3 ${
                          isDivergedHere 
                            ? 'bg-amber-50 border-amber-500/40 hover:border-amber-500' 
                            : 'bg-white border-black/5 opacity-60 hover:opacity-100'
                        }`}
                      >
                        <div className="min-w-0">
                          <span className="font-serif font-bold text-xs text-stone-900 block truncate">{sld.name}</span>
                          <span className="text-[10px] text-stone-500 font-serif block line-clamp-1">{sld.description}</span>
                        </div>
                        <button
                          onClick={() => handleSidelineClick(sld)}
                          className="px-2.5 py-1 text-[9px] font-sans font-bold bg-[#D97706] hover:bg-[#D97706]/90 text-white uppercase tracking-wider rounded transition-all whitespace-nowrap"
                        >
                          Explore
                        </button>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          )}

          {/* Autoplay pace control */}
          <div className="mt-4 pt-4 border-t border-black/10 flex flex-wrap items-center justify-between gap-3 text-stone-600">
            <div className="flex items-center gap-2">
              <button
                onClick={() => setIsPlaying(!isPlaying)}
                className={`flex items-center gap-1 px-4 py-1.5 rounded uppercase text-[9px] font-bold transition-all border font-sans ${
                  isPlaying 
                    ? 'bg-amber-800 text-white border-amber-800 hover:bg-amber-900' 
                    : 'bg-[#1A1A1A] text-white border-[#1A1A1A] hover:bg-black'
                }`}
              >
                {isPlaying ? <Pause size={10} /> : <Play size={10} />}
                <span>{isPlaying ? 'Pause' : 'Autoplay'}</span>
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

      {/* RIGHT COLUMN: Chapter explorer & Interactive Variation Tree */}
      <div className="lg:col-span-7 flex flex-col gap-6 text-left">
        {/* Chapter Explorer (Accordion) */}
        <div className="bg-[#141414] text-white border border-white/5 rounded-2xl p-6 shadow-md flex-grow">
          <span className="text-[10px] font-mono uppercase tracking-widest opacity-40 block mb-2">
            CHAPTER EXPLORER
          </span>
          <h3 className="text-xl font-serif text-white font-light tracking-tight mb-4">
            Study Playbook: King's Indian Structure
          </h3>
          
          <div className="space-y-3 max-h-[300px] overflow-y-auto pr-1">
            {chapterGroups.map((group) => {
              const isOpen = !!openChapters[group.chapterNumber];
              return (
                <div key={group.chapterNumber} className="border-b border-white/5 pb-2">
                  <button
                    onClick={() => toggleChapter(group.chapterNumber)}
                    className="w-full flex items-center justify-between py-2 text-left font-serif hover:text-[#D97706] transition-colors"
                  >
                    <div className="flex items-baseline gap-2">
                      <span className="text-xs font-mono opacity-40">Ch.{group.chapterNumber}</span>
                      <span className="font-medium text-sm text-stone-200">{group.chapterTitle}</span>
                    </div>
                    {isOpen ? <ChevronDown size={14} className="opacity-50" /> : <ChevronRight size={14} className="opacity-50" />}
                  </button>
                  
                  {isOpen && (
                    <div className="pl-6 pt-1 pb-2 space-y-1.5">
                      {group.items.map((ex) => {
                        const isActive = ex.id === selectedExerciseId;
                        return (
                          <div
                            key={ex.id}
                            onClick={() => setSelectedExerciseId(ex.id)}
                            className={`p-2.5 rounded border text-left cursor-pointer transition-all ${
                              isActive
                                ? 'bg-white/10 border-white text-white font-semibold'
                                : 'bg-white/5 border-transparent text-gray-400 hover:text-white hover:bg-white/10'
                            }`}
                          >
                            <div className="text-[11px] font-sans leading-tight">{ex.title}</div>
                            <div className="text-[9px] font-serif italic mt-0.5 opacity-50">{ex.description}</div>
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>

        {/* Interactive Variation Tree timeline */}
        <div className="bg-[#141414] text-white border border-white/5 rounded-2xl p-6 shadow-md flex-grow">
          <div className="flex justify-between items-center mb-4">
            <div>
              <span className="text-[10px] font-mono uppercase tracking-widest opacity-40 block mb-1">
                VARIATION TIMELINE
              </span>
              <h3 className="text-lg font-serif text-white font-light tracking-tight">
                {isExploringOpening ? 'Opening Setup Sequence' : 'Middle Game Theoretical Path'}
              </h3>
            </div>
            
            {openingMoves.length > 0 && (
              <button
                onClick={() => {
                  setIsPlaying(false);
                  setIsExploringOpening(!isExploringOpening);
                }}
                className={`text-[9px] font-sans font-bold px-2 py-1 rounded transition-colors uppercase tracking-wider border pointer-events-auto cursor-pointer ${
                  isExploringOpening 
                    ? 'bg-amber-600/25 border-amber-500 text-amber-400 font-semibold' 
                    : 'bg-white/5 border-white/10 hover:bg-white/10 text-stone-300'
                }`}
              >
                {isExploringOpening ? 'Switch to Theory puzzle' : '🎓 Walkthrough opening'}
              </button>
            )}
          </div>

          <div className="space-y-1.5 bg-black/40 border border-white/5 p-3 rounded-xl max-h-[350px] overflow-y-auto">
            {isExploringOpening ? (
              openingMoves.map((m, index) => {
                const isActive = currentOpeningMoveIndex === index;
                return (
                  <div
                    key={`open_tree_${index}`}
                    onClick={() => setCurrentOpeningMoveIndex(index)}
                    className={`flex items-baseline justify-between p-2.5 cursor-pointer rounded transition-all ${
                      isActive
                        ? 'bg-amber-900/30 text-white border-l-2 border-[#D97706]'
                        : 'hover:bg-white/5 text-gray-400 hover:text-gray-250'
                    }`}
                  >
                    <div className="flex items-baseline gap-3 min-w-0 flex-1">
                      <span className="w-8 text-[11px] text-gray-600 text-right shrink-0 font-mono">
                        {m.move_number}{m.player === 'W' ? '.' : '...'}
                      </span>
                      <span className={`px-1.5 py-0.5 rounded text-xs font-bold shrink-0 ${
                        isActive ? 'text-amber-300 bg-amber-950/40' : 'text-stone-300 bg-stone-900/30'
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
            ) : (
              gameMoves.length === 0 ? (
                <div className="p-8 text-center text-gray-500 italic text-xs font-sans">
                  No moves extracted. Go to Digitizer AI tab to start.
                </div>
              ) : (
                gameMoves.map((m, index) => {
                  const isActive = currentMoveIndex === index;
                  return (
                    <div
                      key={`main_tree_${index}`}
                      onClick={() => setCurrentMoveIndex(index)}
                      className={`flex items-baseline justify-between p-2.5 cursor-pointer rounded transition-all ${
                        isActive
                          ? 'bg-white/10 text-white border-l-2 border-[#D97706]'
                          : 'hover:bg-white/5 text-gray-400 hover:text-gray-250'
                      }`}
                    >
                      <div className="flex items-baseline gap-3 min-w-0 flex-1">
                        <span className="w-8 text-[11px] text-gray-600 text-right shrink-0 font-mono">
                          {m.move_number}{m.player === 'W' ? '.' : '...'}
                        </span>
                        <span className={`px-1.5 py-0.5 rounded text-xs font-bold shrink-0 ${
                          isActive ? 'text-amber-300 bg-amber-900/20' : 'text-blue-300 bg-blue-950/20'
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
              )
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
