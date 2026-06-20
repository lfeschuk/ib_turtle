import React, { useState, useEffect, useMemo } from 'react';
import { Chess, Square } from 'chess.js';
import { RefreshCw, Undo2, ArrowLeft, ArrowRight, ChevronsLeft, ChevronsRight, HelpCircle } from 'lucide-react';
import { SidelineVariation } from '../types';

const getPieceNameAndSymbol = (p: string | undefined, color: 'w' | 'b' | string) => {
  const symbolMap: { [key: string]: string } = {
    p: color === 'w' ? '♙' : '♟',
    n: color === 'w' ? '♘' : '♞',
    b: color === 'w' ? '♗' : '♝',
    r: color === 'w' ? '♖' : '♜',
    q: color === 'w' ? '♕' : '♛',
    k: color === 'w' ? '♔' : '♚',
  };
  const nameMap: { [key: string]: string } = {
    p: 'Pawn',
    n: 'Knight',
    b: 'Bishop',
    r: 'Rook',
    q: 'Queen',
    k: 'King',
  };
  if (!p) {
    return {
      symbol: color === 'w' ? '♙' : '♟',
      name: 'Piece'
    };
  }
  const pieceKey = p.toLowerCase();
  return {
    symbol: symbolMap[pieceKey] || '♟',
    name: nameMap[pieceKey] || 'Piece'
  };
};

const forcePlaySAN = (chess: Chess, san: string, playerColor: 'w' | 'b') => {
  const cleanSan = san.replace(/[?!+#=]/g, '');
  
  // Castle moves
  if (cleanSan === 'O-O') {
    const rank = playerColor === 'w' ? '1' : '8';
    chess.remove(`e${rank}` as Square);
    chess.remove(`h${rank}` as Square);
    chess.put({ type: 'k', color: playerColor }, `g${rank}` as Square);
    chess.put({ type: 'r', color: playerColor }, `f${rank}` as Square);
  } else if (cleanSan === 'O-O-O') {
    const rank = playerColor === 'w' ? '1' : '8';
    chess.remove(`e${rank}` as Square);
    chess.remove(`a${rank}` as Square);
    chess.put({ type: 'k', color: playerColor }, `c${rank}` as Square);
    chess.put({ type: 'r', color: playerColor }, `d${rank}` as Square);
  } else {
    // Find destination square
    const destMatch = cleanSan.match(/([a-h][1-8])/);
    if (!destMatch) return;
    const destSquare = destMatch[1] as Square;

    // Find piece type
    const pieceChar = cleanSan[0];
    let type: any = 'p';
    if (['K','Q','R','B','N'].includes(pieceChar)) {
      type = pieceChar.toLowerCase();
    }

    // Find source piece of the same type and color that can be removed
    const board = chess.board();
    let sourceSquare: Square | null = null;
    let fallbackSquare: Square | null = null;

    if (type === 'p') {
      // Pawns always have a source file equal to the first character of cleanSan ('a'-'h')
      const sourceFile = cleanSan[0];
      const destRank = parseInt(destSquare[1]);
      let minRankDiff = 99;

      for (let r = 0; r < 8; r++) {
        for (let f = 0; f < 8; f++) {
          const piece = board[r][f];
          if (piece && piece.color === playerColor && piece.type === 'p') {
            const square = `${String.fromCharCode(97 + f)}${8 - r}` as Square;
            if (square === destSquare) continue;

            if (square.startsWith(sourceFile)) {
              const srcRank = parseInt(square[1]);
              // Standard direction check (white moves up, black moves down)
              if (playerColor === 'w' && srcRank >= destRank) continue;
              if (playerColor === 'b' && srcRank <= destRank) continue;

              const diff = Math.abs(srcRank - destRank);
              if (diff < minRankDiff) {
                minRankDiff = diff;
                sourceSquare = square;
              }
            } else {
              // Only fallback if the pawn is on an adjacent file (capture transition)
              // or on the destination file itself
              const destFileChar = destSquare[0];
              const fileIndex = f;
              const sourceFileIndex = sourceFile.charCodeAt(0) - 97;
              const destFileIndex = destFileChar.charCodeAt(0) - 97;
              
              const isAdjacentToSource = Math.abs(fileIndex - sourceFileIndex) <= 1;
              const isAdjacentToDest = Math.abs(fileIndex - destFileIndex) <= 1;
              
              if (isAdjacentToSource || isAdjacentToDest) {
                fallbackSquare = square;
              }
            }
          }
        }
      }
    } else {
      // Find source piece of the same type and color for non-pawn pieces
      const disambiguate = cleanSan.slice(1, cleanSan.indexOf(destSquare));
      
      for (let r = 0; r < 8; r++) {
        for (let f = 0; f < 8; f++) {
          const piece = board[r][f];
          if (piece && piece.color === playerColor && piece.type === type) {
            const square = `${String.fromCharCode(97 + f)}${8 - r}` as Square;
            if (square === destSquare) continue;
            
            // Prefer pieces matching file/rank disambiguation
            if (disambiguate) {
              if (disambiguate.match(/^[a-h]$/) && !square.startsWith(disambiguate)) {
                continue;
              }
              if (disambiguate.match(/^[1-8]$/) && !square.endsWith(disambiguate)) {
                continue;
              }
            }
            sourceSquare = square;
            break;
          }
        }
        if (sourceSquare) break;
      }
    }

    const finalSource = sourceSquare || fallbackSquare;
    if (finalSource) {
      chess.remove(finalSource);
    }
    chess.remove(destSquare);
    chess.put({ type, color: playerColor }, destSquare);
  }

  // Force active turn toggle for sequential play
  const tokens = chess.fen().split(' ');
  tokens[1] = playerColor === 'w' ? 'b' : 'w';
  try {
    chess.load(tokens.join(' '));
  } catch (err) {
    // Fallback if load is blocked by king check or validation rules
  }
};

interface ChessBoardProps {
  initialMoves?: string;
  gameMoves?: Array<{ move: string; player: 'W' | 'B'; move_number: number }>;
  currentMoveIndex: number; // Index in the interactive moves array (-1 means before the starting move)
  onMoveSelected?: (index: number) => void;
  onCustomMovePlayed?: (fen: string, san: string) => void;
  isCorrectionMode?: boolean;
  onCorrectMoveParsed?: (nextIdx: number) => void;
  onIncorrectMoveParsed?: (playedSAN: string, expectedSAN: string) => void;
  sidelines?: SidelineVariation[];
  onAlternateSidelinePlayed?: (sld: SidelineVariation) => void;
  solitaireFrontierIndex?: number;
  solitaireSidelineFrontierIndex?: number;
  activeSideline?: SidelineVariation | null;
  hintLevel?: number;
}

export const ChessBoard: React.FC<ChessBoardProps> = ({
  initialMoves = '',
  gameMoves = [],
  currentMoveIndex,
  onMoveSelected,
  onCustomMovePlayed,
  isCorrectionMode = false,
  onCorrectMoveParsed,
  onIncorrectMoveParsed,
  sidelines = [],
  onAlternateSidelinePlayed,
  solitaireFrontierIndex = -1,
  solitaireSidelineFrontierIndex = -1,
  activeSideline = null,
  hintLevel = 0,
}) => {
  // Setup the base chess state
  const [chessInstance, setChessInstance] = useState<Chess>(() => new Chess());
  const [boardOrientation, setBoardOrientation] = useState<'w' | 'b'>('w');
  const [isCustomPlayMode, setIsCustomPlayMode] = useState(false);
  const [customGameHistory, setCustomGameHistory] = useState<string[]>([]); // custom SAN moves

  // Click-to-move / Highlights states
  const [selectedSquare, setSelectedSquare] = useState<Square | null>(null);
  const [legalDests, setLegalDests] = useState<Square[]>([]);

  // Feedback Flash states
  const [flashState, setFlashState] = useState<'correct' | 'incorrect' | null>(null);

  // Audio Feedback using simple Web Audio API Synthesizer
  const playMoveSound = (captured = false) => {
    try {
      const audioCtx = new (window.AudioContext || (window as any).webkitAudioContext)();
      const osc = audioCtx.createOscillator();
      const gainNode = audioCtx.createGain();
      osc.connect(gainNode);
      gainNode.connect(audioCtx.destination);
      
      if (captured) {
        osc.type = 'triangle';
        osc.frequency.setValueAtTime(320, audioCtx.currentTime);
        osc.frequency.setValueAtTime(240, audioCtx.currentTime + 0.08);
        gainNode.gain.setValueAtTime(0.08, audioCtx.currentTime);
        gainNode.gain.exponentialRampToValueAtTime(0.001, audioCtx.currentTime + 0.18);
        osc.start();
        osc.stop(audioCtx.currentTime + 0.2);
      } else {
        osc.type = 'sine';
        osc.frequency.setValueAtTime(360, audioCtx.currentTime);
        gainNode.gain.setValueAtTime(0.05, audioCtx.currentTime);
        gainNode.gain.exponentialRampToValueAtTime(0.001, audioCtx.currentTime + 0.08);
        osc.start();
        osc.stop(audioCtx.currentTime + 0.1);
      }
    } catch (e) {
      // Audio context might be blocked or unsupported: ignore gracefully
    }
  };

  const playErrorSound = () => {
    try {
      const audioCtx = new (window.AudioContext || (window as any).webkitAudioContext)();
      const osc = audioCtx.createOscillator();
      const gainNode = audioCtx.createGain();
      osc.connect(gainNode);
      gainNode.connect(audioCtx.destination);
      
      osc.type = 'sawtooth';
      osc.frequency.setValueAtTime(140, audioCtx.currentTime);
      osc.frequency.setValueAtTime(120, audioCtx.currentTime + 0.1);
      gainNode.gain.setValueAtTime(0.04, audioCtx.currentTime);
      gainNode.gain.exponentialRampToValueAtTime(0.001, audioCtx.currentTime + 0.25);
      osc.start();
      osc.stop(audioCtx.currentTime + 0.28);
    } catch (e) {
      // Audio context blocked: ignore gracefully
    }
  };

  // Safe cleaner for chess annotation characters
  const cleanSAN = (san: string): string => {
    return san.replace(/[!?#+$]+$/, '');
  };

  // Robust comparison of chess moves, normalizing case, castling (O-O vs o-o vs 0-0) and annotations
  const areMovesEquivalent = (m1: string, m2: string): boolean => {
    const normalize = (s: string) => {
      // lower case, strip checks, annotations, equals sign for promotions
      let r = s.toLowerCase().replace(/[!?#+$=:\s]+/g, '').trim();
      // normalize castling with '0' to 'o'
      r = r.replace(/0/g, 'o');
      return r;
    };
    return normalize(m1) === normalize(m2);
  };

  const activeFrontier = useMemo(() => {
    if (!isCorrectionMode) return gameMoves.length - 1;
    return activeSideline ? solitaireSidelineFrontierIndex : solitaireFrontierIndex;
  }, [isCorrectionMode, activeSideline, solitaireFrontierIndex, solitaireSidelineFrontierIndex, gameMoves.length]);

  const hintSquares = useMemo(() => {
    if (!isCorrectionMode || !hintLevel || hintLevel <= 0) return null;
    
    const nextExpectedIndex = currentMoveIndex + 1;
    const movesList = activeSideline ? activeSideline.moves : gameMoves;
    const expectedMove = movesList[nextExpectedIndex];
    if (!expectedMove) return null;

    const legalMoves = chessInstance.moves({ verbose: true });
    const matched = legalMoves.find(m => areMovesEquivalent(m.san, expectedMove.move));
    
    if (!matched && sidelines && sidelines.length > 0) {
      const matchedSideline = sidelines.find(sld => {
        if (sld.startingMoveIndex === currentMoveIndex && sld.moves.length > 0) {
          return true;
        }
        return false;
      });
      if (matchedSideline) {
        const sldExpectedMove = matchedSideline.moves[0];
        const matchedSldMove = legalMoves.find(m => areMovesEquivalent(m.san, sldExpectedMove.move));
        if (matchedSldMove) {
          return {
            from: matchedSldMove.from,
            to: matchedSldMove.to
          };
        }
      }
    }

    if (matched) {
      return {
        from: matched.from,
        to: matched.to
      };
    }
    return null;
  }, [isCorrectionMode, hintLevel, currentMoveIndex, activeSideline, gameMoves, sidelines, chessInstance]);

  // Re-calculate the board FEN and track the last played move whenever initialMoves, gameMoves, or currentMoveIndex changes
  const { fen: activeFEN, lastMove: lastGameMove } = useMemo(() => {
    const tempChess = new Chess();
    let lastM: any = null;
    
    // 1. Play initial setups
    if (initialMoves) {
      if (initialMoves.trim().includes('/')) {
        try {
          tempChess.load(initialMoves.trim());
        } catch (e) {
          console.warn("Could not load initial FEN", e);
        }
      } else {
        const cleanInitial = initialMoves
          .replace(/\d+\.+/g, '') // remove move numbers like 1. or 14...
          .replace(/\s+/g, ' ')
          .trim()
          .split(' ');

        for (const rawMove of cleanInitial) {
          if (!rawMove) continue;
          const cleaned = cleanSAN(rawMove);
          try {
            const mRes = tempChess.move(cleaned);
            lastM = mRes;
          } catch (err) {
            console.warn(`Could not make initial move: "${rawMove}" (cleaned as "${cleaned}") - using forcePlaySAN`);
            forcePlaySAN(tempChess, cleaned, tempChess.turn());
          }
        }
      }
    }

    // 2. Play game moves up to the selected index
    for (let i = 0; i <= currentMoveIndex; i++) {
      if (gameMoves[i] && i < gameMoves.length) {
        const cleaned = cleanSAN(gameMoves[i].move);
        try {
          const mRes = tempChess.move(cleaned);
          lastM = mRes;
        } catch (err) {
          console.warn(`Could not make interactive move at index ${i}: "${gameMoves[i].move}" (cleaned as "${cleaned}") - using forcePlaySAN`);
          const turnColor = gameMoves[i].player === 'W' ? 'w' : 'b';
          forcePlaySAN(tempChess, cleaned, turnColor);
          
          let pieceLetter = 'p';
          if (cleaned) {
            const firstChar = cleaned[0];
            if (['K','Q','R','B','N'].includes(firstChar)) {
              pieceLetter = firstChar.toLowerCase();
            }
          }
          
          const destMatch = cleaned.match(/([a-h][1-8])/);
          const toSquare = destMatch ? destMatch[1] : '';

          lastM = { 
            san: gameMoves[i].move, 
            color: turnColor,
            piece: pieceLetter,
            from: '',
            to: toSquare
          };
        }
      }
    }

    return {
      fen: tempChess.fen(),
      lastMove: lastM
    };
  }, [initialMoves, gameMoves, currentMoveIndex]);

  // Sync board with active FEN computed
  useEffect(() => {
    try {
      const nextGame = new Chess(activeFEN);
      setChessInstance(nextGame);
    } catch (e) {
      console.warn("Failed to instantiate Chess engine with active FEN:", activeFEN, e);
    }
    setIsCustomPlayMode(false);
    setCustomGameHistory([]);
    setSelectedSquare(null);
    setLegalDests([]);
    setFlashState(null);
  }, [activeFEN]);

  // Derive highlight for the last move (either custom or mainline book move)
  const lastMoveHighlight = useMemo(() => {
    if (isCustomPlayMode) {
      const history = chessInstance.history({ verbose: true });
      return history.length > 0 ? history[history.length - 1] : null;
    }
    return lastGameMove;
  }, [isCustomPlayMode, chessInstance, lastGameMove]);

  // Derive the absolute move number and color of the custom played line to avoid hardcoded approximations
  const { startMoveNumber, startPlayer } = useMemo(() => {
    if (currentMoveIndex >= 0 && gameMoves[currentMoveIndex]) {
      const lastM = gameMoves[currentMoveIndex];
      if (lastM.player === 'W') {
        return { startMoveNumber: lastM.move_number, startPlayer: 'B' as 'W' | 'B' };
      } else {
        return { startMoveNumber: lastM.move_number + 1, startPlayer: 'W' as 'W' | 'B' };
      }
    } else if (gameMoves.length > 0) {
      return { startMoveNumber: gameMoves[0].move_number, startPlayer: gameMoves[0].player };
    }
    return { startMoveNumber: 1, startPlayer: 'W' as 'W' | 'B' };
  }, [gameMoves, currentMoveIndex]);

  // Execute actual chess move and handle Solitaire or free branches
  const executeMove = (from: Square, to: Square) => {
    try {
      // Find the legal move matching this from/to from current engine state
      const legalMoves = chessInstance.moves({ verbose: true });
      const playedMove = legalMoves.find(m => m.from === from && m.to === to);

      if (!playedMove) {
        playErrorSound();
        setSelectedSquare(null);
        setLegalDests([]);
        return;
      }

      if (isCorrectionMode) {
        const nextExpectedIndex = currentMoveIndex + 1;
        const expectedMove = gameMoves[nextExpectedIndex];

        // Match against standard expected mainline move
        let isMatch = false;
        let matchedSideline: SidelineVariation | undefined = undefined;

        if (expectedMove && areMovesEquivalent(playedMove.san, expectedMove.move)) {
          isMatch = true;
        }

        // Match against sidelines
        if (!isMatch && sidelines && sidelines.length > 0) {
          matchedSideline = sidelines.find(sld => {
            if (sld.startingMoveIndex === currentMoveIndex && sld.moves.length > 0) {
              return areMovesEquivalent(playedMove.san, sld.moves[0].move);
            }
            return false;
          });
          if (matchedSideline) {
            isMatch = true;
          }
        }

        if (isMatch) {
          playMoveSound(!!playedMove.captured);
          setFlashState('correct');
          setTimeout(() => setFlashState(null), 850);

          // Construct the new chess state by making the REAL move
          const nextChess = new Chess(chessInstance.fen());
          nextChess.move({ from, to, promotion: 'q' });
          setChessInstance(nextChess);

          if (matchedSideline) {
            if (onAlternateSidelinePlayed) {
              onAlternateSidelinePlayed(matchedSideline);
            }
          } else {
            if (onCorrectMoveParsed) {
              onCorrectMoveParsed(nextExpectedIndex);
            }
          }
          setSelectedSquare(null);
          setLegalDests([]);
          return;
        } else {
          // Wrong Solitaire move played
          playErrorSound();
          setFlashState('incorrect');
          setTimeout(() => setFlashState(null), 850);

          if (onIncorrectMoveParsed) {
            onIncorrectMoveParsed(playedMove.san, expectedMove ? expectedMove.move : 'none');
          }
          setSelectedSquare(null);
          setLegalDests([]);
          return;
        }
      }

      // Normal or Custom Play Mode
      const testChess = new Chess(chessInstance.fen());
      const matchedMove = testChess.move({
        from,
        to,
        promotion: 'q',
      });

      if (matchedMove) {
        playMoveSound(!!matchedMove.captured);
        const nextFen = testChess.fen();
        setChessInstance(new Chess(nextFen));
        
        if (onCustomMovePlayed) {
          onCustomMovePlayed(nextFen, matchedMove.san);
        }
        
        setIsCustomPlayMode(true);
        setCustomGameHistory(prev => [...prev, matchedMove.san]);
      } else {
        playErrorSound();
      }
    } catch (err) {
      console.error("Error in executeMove:", err);
      playErrorSound();
    }
    setSelectedSquare(null);
    setLegalDests([]);
  };

  // Interact: Click a square
  const handleSquareClick = (squareName: Square) => {
    const piece = chessInstance.get(squareName);

    // If a legal destination is clicked
    if (legalDests.includes(squareName) && selectedSquare) {
      executeMove(selectedSquare, squareName);
      return;
    }

    // Otherwise, attempt selection
    if (piece) {
      // Check turn colors in solitaire: allow picking any of side to play, or both in analysis
      const isPickable = !isCorrectionMode || (piece.color === chessInstance.turn() && currentMoveIndex === activeFrontier);
      if (isPickable) {
        setSelectedSquare(squareName);
        const moves = chessInstance.moves({ square: squareName, verbose: true });
        setLegalDests(moves.map(m => m.to as Square));
      } else {
        setSelectedSquare(null);
        setLegalDests([]);
      }
    } else {
      setSelectedSquare(null);
      setLegalDests([]);
    }
  };

  // Drag and Drop support
  const handleDragStart = (e: React.DragEvent, squareName: Square) => {
    const piece = chessInstance.get(squareName);
    const isPickable = !isCorrectionMode || (piece && piece.color === chessInstance.turn() && currentMoveIndex === activeFrontier);
    
    if (piece && isPickable) {
      e.dataTransfer.setData("text/plain", squareName);
      setSelectedSquare(squareName);
      const moves = chessInstance.moves({ square: squareName, verbose: true });
      setLegalDests(moves.map(m => m.to as Square));
    } else {
      e.preventDefault();
    }
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
  };

  const handleDrop = (e: React.DragEvent, targetSquare: Square) => {
    e.preventDefault();
    const sourceSquare = e.dataTransfer.getData("text/plain") as Square;
    if (sourceSquare && sourceSquare !== targetSquare) {
      executeMove(sourceSquare, targetSquare);
    }
  };

  // Layout calculations
  const files = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h'];
  const ranks = ['8', '7', '6', '5', '4', '3', '2', '1'];

  const displayFiles = boardOrientation === 'w' ? files : [...files].reverse();
  const displayRanks = boardOrientation === 'w' ? ranks : [...ranks].reverse();

  return (
    <div id="chessboard-container" className="flex flex-col items-center w-full max-w-[480px] bg-amber-50/50 border border-amber-900/10 shadow-md rounded-2xl p-4">
      
      {/* Board Indicator Bar */}
      <div className="flex justify-between items-center w-full pb-3 border-b border-amber-900/10 text-xs text-stone-900 font-sans">
        <div className="flex items-center gap-2">
          <span className={`w-3 h-3 rounded-full shadow-inner ${chessInstance.turn() === 'w' ? 'bg-white border border-stone-400' : 'bg-stone-900'}`}></span>
          <span className="font-sans font-bold uppercase tracking-wider text-[10px] text-stone-700">
            {chessInstance.turn() === 'w' ? "White to play" : "Black to play"}
          </span>
          {isCustomPlayMode && (
            <span className="px-2 py-0.5 text-[9px] bg-[#B91C1C] text-white font-sans uppercase tracking-widest font-bold rounded">
              Analysis Mode
            </span>
          )}
        </div>
        <button
          onClick={() => setBoardOrientation(prev => prev === 'w' ? 'b' : 'w')}
          className="text-[10px] font-sans uppercase tracking-wider text-amber-900/80 hover:text-amber-900 hover:bg-amber-100/50 flex items-center gap-1.5 transition-all px-2.5 py-1 border border-amber-900/10 hover:border-amber-900/30 rounded-lg cursor-pointer"
          title="Flip Chessboard View"
        >
          <RefreshCw size={10} />
          <span>Flip Board</span>
        </button>
      </div>

      {/* Elegant Last Move & Piece tracker */}
      {lastMoveHighlight ? (
        <div className="w-full flex items-center justify-between mt-2.5 px-3 py-1.5 bg-amber-100/40 border border-amber-900/10 rounded-xl text-xs font-serif text-stone-850 shadow-2xs">
          <div className="flex items-center gap-2">
            <span className="text-amber-900 font-extrabold font-sans text-[9px] tracking-wider uppercase">Moved:</span>
            <span className="font-sans text-xs text-stone-950 font-bold flex items-center gap-1.5">
              <span className="text-base leading-none text-amber-900/90 select-none">{getPieceNameAndSymbol(lastMoveHighlight.piece, lastMoveHighlight.color).symbol}</span>
              <span className="text-amber-950 font-mono font-extrabold text-[9px] uppercase bg-amber-900/10 px-1 py-0.5 rounded select-none">{getPieceNameAndSymbol(lastMoveHighlight.piece, lastMoveHighlight.color).name}</span>
              <span className="text-[11px] font-sans font-extrabold text-stone-950 bg-white px-2 py-0.5 rounded border border-stone-200 shadow-3xs">{lastMoveHighlight.san}</span>
            </span>
          </div>
          <div className="text-[10px] font-mono text-stone-550 bg-white/60 border border-stone-100 rounded px-1.5 py-0.5 font-bold">
            <span>{lastMoveHighlight.from} → {lastMoveHighlight.to}</span>
          </div>
        </div>
      ) : (
        <div className="w-full text-center mt-2.5 py-1.5 bg-stone-55 border border-stone-200/60 rounded-xl text-[10px] font-sans text-stone-400 font-medium select-none">
          Start position. No moves played yet.
        </div>
      )}

      {/* Grid Container */}
      <div 
        className={`w-full aspect-square relative my-4 p-[3px] border-[5px] border-amber-950/90 rounded-xl overflow-hidden shadow-xl transition-all duration-300 ${
          flashState === 'correct' 
            ? 'ring-4 ring-green-500 shadow-green-200' 
            : flashState === 'incorrect' 
              ? 'ring-4 ring-red-500 shadow-red-200 animate-shake' 
              : 'shadow-stone-300'
        }`}
      >
        <div className="w-full h-full grid grid-cols-8 grid-rows-8 bg-amber-950">
          {displayRanks.map((rank, rankIdx) => 
            displayFiles.map((file, fileIdx) => {
              const squareName = `${file}${rank}` as Square;
              const piece = chessInstance.get(squareName);
              const isDark = (rankIdx + fileIdx) % 2 === 1;
              const isSelected = selectedSquare === squareName;
              const isTargetMove = legalDests.includes(squareName);

              // Check if this square is highlighted as part of the last move
              const isLastMoveFrom = lastMoveHighlight && lastMoveHighlight.from === squareName;
              const isLastMoveTo = lastMoveHighlight && lastMoveHighlight.to === squareName;
              const isLastMoveHighlight = isLastMoveFrom || isLastMoveTo;

              // Square Colors: Cream vs Rich Warm Brown Wood color scheme
              const baseBg = isDark ? 'bg-[#9F7657]' : 'bg-[#FAF4EB]';
              const textTint = isDark ? 'text-[#FAF4EB]' : 'text-[#9F7657]';

              // Visual indicators
              let highlightBg = '';
              if (isSelected) {
                highlightBg = 'ring-4 ring-amber-400 ring-inset bg-amber-400/20';
              } else if (hintSquares) {
                const isHintFrom = hintSquares.from === squareName;
                const isHintTo = hintSquares.to === squareName;
                if (hintLevel === 1 && isHintFrom) {
                  highlightBg = 'ring-4 ring-amber-500 ring-inset bg-amber-500/25 animate-pulse';
                } else if (hintLevel === 2 && (isHintFrom || isHintTo)) {
                  highlightBg = isHintFrom 
                    ? 'ring-4 ring-amber-500 ring-inset bg-amber-500/25 animate-pulse'
                    : 'ring-4 ring-blue-500 ring-inset bg-blue-500/25 animate-pulse';
                }
              }

              // Get piece visual code
              let pieceImgUrl = '';
              if (piece) {
                const pColor = piece.color;
                const pType = piece.type.toUpperCase();
                // Load premium Lichess vector piece elements (cburnett theme)
                pieceImgUrl = `https://lichess1.org/assets/piece/cburnett/${pColor}${pType}.svg`;
              }

              return (
                <div
                  key={squareName}
                  onClick={() => handleSquareClick(squareName)}
                  onDragOver={handleDragOver}
                  onDrop={(e) => handleDrop(e, squareName)}
                  className={`relative aspect-square flex items-center justify-center cursor-pointer transition-all ${baseBg} ${highlightBg} select-none`}
                >
                  {/* Last move highlight overlay */}
                  {isLastMoveHighlight && (
                    <div className="absolute inset-0 bg-[#E1D339]/35 mix-blend-multiply pointer-events-none z-0" />
                  )}

                  {/* Chess piece graphic */}
                  {piece && (
                    <img
                      src={pieceImgUrl}
                      alt={`${piece.color === 'w' ? 'White' : 'Black'} ${piece.type}`}
                      draggable="true"
                      onDragStart={(e) => handleDragStart(e, squareName)}
                      className="w-[85%] h-[85%] object-contain select-none z-10 transition-transform hover:scale-105 active:scale-95 cursor-grab active:cursor-grabbing"
                      referrerPolicy="no-referrer"
                    />
                  )}

                  {/* Translucent circle highlight for legal target squares */}
                  {isTargetMove && (
                    <div className="absolute inset-0 flex items-center justify-center z-20 pointer-events-none">
                      {piece ? (
                        // Ring around a captures target
                        <div className="w-[82%] h-[82%] rounded-full border-4 border-amber-500/60" />
                      ) : (
                        // Simple dot on empty legal squares
                        <div className="w-3 h-3 md:w-4 md:h-4 bg-amber-800/40 rounded-full" />
                      )}
                    </div>
                  )}

                  {/* Column Coordinates labels on files on the bottom rank */}
                  {rankIdx === 7 && (
                    <span className={`absolute bottom-0.5 left-0.5 text-[8px] font-sans font-bold tracking-wider opacity-60 uppercase select-none pointer-events-none ${textTint}`}>
                      {file}
                    </span>
                  )}

                  {/* Row Coordinates labels on ranks on the right file */}
                  {fileIdx === 7 && (
                    <span className={`absolute top-0.5 right-0.5 text-[8px] font-sans font-bold opacity-60 select-none pointer-events-none ${textTint}`}>
                      {rank}
                    </span>
                  )}
                </div>
              );
            })
          )}
        </div>
      </div>

      {/* Control Navigation Keys */}
      <div className="flex justify-between items-center w-full pt-2 border-t border-amber-900/10 gap-2">
        <div className="flex gap-1">
          <button
            onClick={() => onMoveSelected && onMoveSelected(-1)}
            disabled={currentMoveIndex === -1 && !isCustomPlayMode}
            className="p-2 bg-white text-[#1A1A1A] hover:bg-amber-100 disabled:opacity-30 disabled:hover:bg-white rounded-lg border border-amber-900/10 transition-colors cursor-pointer"
            title="Jump to Start"
          >
            <ChevronsLeft size={14} />
          </button>
          
          <button
            onClick={() => onMoveSelected && onMoveSelected(currentMoveIndex - 1)}
            disabled={currentMoveIndex === -1 && !isCustomPlayMode}
            className="p-2 bg-white text-[#1A1A1A] hover:bg-amber-100 disabled:opacity-30 disabled:hover:bg-white rounded-lg border border-amber-900/10 transition-colors cursor-pointer"
            title="Previous Move"
          >
            <ArrowLeft size={14} />
          </button>
        </div>

        {/* Sync / Reset active annotation visual indicator */}
        <div className="text-center font-sans">
          {isCorrectionMode ? (
            <span className="text-[9px] font-sans font-bold text-red-700 bg-red-50 border border-red-200 px-3 py-1 uppercase tracking-wider rounded-lg block shadow-xs animate-pulse">
              🎯 SOLITAIRE ACTIVE
            </span>
          ) : isCustomPlayMode ? (
            <button
              onClick={() => {
                setIsCustomPlayMode(false);
                const restored = new Chess(activeFEN);
                setChessInstance(restored);
                setCustomGameHistory([]);
                playMoveSound(false);
              }}
              className="flex items-center gap-1.5 px-3 py-1 bg-[#1A1A1A] text-white hover:bg-black rounded-lg text-[9px] font-bold uppercase tracking-wider transition-all shadow-sm cursor-pointer"
            >
              <Undo2 size={10} />
              <span>Reset Branch</span>
            </button>
          ) : (
            <span className="text-[9px] font-sans text-stone-500 uppercase tracking-widest font-bold block px-2 py-1 select-none">
              {currentMoveIndex === -1 ? 'Initial Position' : `Move ${currentMoveIndex + 1} of ${gameMoves.length}`}
            </span>
          )}
        </div>

        <div className="flex gap-1">
          <button
            onClick={() => onMoveSelected && onMoveSelected(currentMoveIndex + 1)}
            disabled={currentMoveIndex >= gameMoves.length - 1 || isCustomPlayMode || (isCorrectionMode && currentMoveIndex >= activeFrontier)}
            className="p-2 bg-white text-[#1A1A1A] hover:bg-amber-100 disabled:opacity-30 disabled:hover:bg-white rounded-lg border border-amber-900/10 transition-colors cursor-pointer"
            title="Next Move"
          >
            <ArrowRight size={14} />
          </button>
          
          <button
            onClick={() => onMoveSelected && onMoveSelected(gameMoves.length - 1)}
            disabled={currentMoveIndex >= gameMoves.length - 1 || isCustomPlayMode || (isCorrectionMode && currentMoveIndex >= activeFrontier)}
            className="p-2 bg-white text-[#1A1A1A] hover:bg-amber-100 disabled:opacity-30 disabled:hover:bg-white rounded-lg border border-[#B91C1C]/10 transition-colors cursor-pointer"
            title="Jump to End"
          >
            <ChevronsRight size={14} />
          </button>
        </div>
      </div>

      {isCustomPlayMode && (
        <div className="w-full mt-3.5 p-3 bg-white border border-amber-900/15 rounded-xl text-left shadow-xs">
          <div className="flex justify-between items-center mb-1 select-none">
            <div className="font-bold text-amber-900 font-sans uppercase tracking-widest text-[9px]">Custom Analysis Line:</div>
            {!isCorrectionMode && (
              <span className="text-[9.5px] text-[#B91C1C] font-semibold font-sans animate-pulse">
                💡 Tip: Turn on "Solitaire Trainer" below!
              </span>
            )}
          </div>
          <div className="flex flex-wrap gap-1.5 mt-1">
            {customGameHistory.length === 0 ? (
              <span className="italic text-[10px] text-stone-500">Play manual moves on the board above to map out variations...</span>
            ) : (
              customGameHistory.map((mStr, idx) => {
                const moveNum = startMoveNumber + Math.floor((idx + (startPlayer === 'B' ? 1 : 0)) / 2);
                const isWhiteMoveOfPair = (startPlayer === 'W' && idx % 2 === 0) || (startPlayer === 'B' && idx % 2 === 1);
                return (
                  <span key={idx} className="bg-amber-50/50 border border-amber-900/10 px-1.5 py-0.5 rounded text-amber-950 font-mono text-xs shadow-3xs">
                    {isWhiteMoveOfPair ? `${moveNum}. ` : idx === 0 && startPlayer === 'B' ? `${moveNum}... ` : ''}{mStr}
                  </span>
                );
              })
            )}
          </div>
        </div>
      )}
    </div>
  );
};
