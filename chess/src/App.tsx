import React, { useState, useEffect, useRef, useMemo } from 'react';
import { 
  BookOpen, 
  Sparkles, 
  FileCode, 
  Play, 
  Pause, 
  Copy, 
  Check, 
  Upload, 
  AlertCircle, 
  RotateCcw, 
  Trash2, 
  FileText, 
  ChevronRight, 
  ArrowRight,
  Info,
  Layers,
  Sparkle,
  Trophy
} from 'lucide-react';
import { ChessBoard } from './components/ChessBoard';
import { SAMPLE_PAGES } from './sampleData';
import { ParsedChessGame, ChessMove, SidelineVariation, SampleBookPage, ChessBook } from './types';
import { getOpeningMovesForPage } from './openingExplainer';
import { LearningSection } from './components/LearningSection';
import { GamesSection } from './components/GamesSection';
import { ExercisesSection } from './components/ExercisesSection';

export default function App() {
  const LOCAL_STORAGE_KEY = 'chess_codex_books_v3';

  // Custom alert/toast notifications state
  const [alertState, setAlertState] = useState<{ message: string; type: 'success' | 'error' | 'info' } | null>(null);
  
  // Custom Confirm Dialog state
  const [confirmState, setConfirmState] = useState<{ message: string; onConfirm: () => void } | null>(null);

  const singlePageAbortControllerRef = useRef<AbortController | null>(null);
  const fullBookAbortControllerRef = useRef<AbortController | null>(null);

  const showAlert = (message: string, type: 'success' | 'error' | 'info' = 'info') => {
    setAlertState({ message, type });
    setTimeout(() => {
      setAlertState(prev => prev?.message === message ? null : prev);
    }, 4500);
  };

  const showConfirm = (message: string, onConfirm: () => void) => {
    setConfirmState({ message, onConfirm });
  };

  const handleCancelSinglePageParsing = () => {
    if (singlePageAbortControllerRef.current) {
      singlePageAbortControllerRef.current.abort();
      singlePageAbortControllerRef.current = null;
    }
    setIsParsing(false);
    showAlert("Single page compilation successfully canceled.", "info");
  };

  const handleCancelFullBookParsing = () => {
    if (fullBookAbortControllerRef.current) {
      fullBookAbortControllerRef.current.abort();
      fullBookAbortControllerRef.current = null;
    }
    setIsParsingFullBook(false);
    showAlert("Full book compilation successfully canceled.", "info");
  };

  // Application Data States - Books and Selected Book ID
  const [books, setBooks] = useState<ChessBook[]>(() => {
    const saved = localStorage.getItem(LOCAL_STORAGE_KEY);
    if (saved) {
      try {
        const parsed = JSON.parse(saved) as ChessBook[];
        // Auto-migration: If default book_1 exists but is missing the newly added 68 illustrative games,
        // we upgrade its exercises list automatically so the user gets them instantly.
        return parsed.map((b) => {
          if (b.id === 'book_1') {
            const hasIllustrativeGames = b.exercises.some((e) => e.id.startsWith('game_') && e.id !== 'game_1_tactical_trap');
            if (!hasIllustrativeGames || b.exercises.length < SAMPLE_PAGES.length) {
              return {
                ...b,
                title: "Joe Gallagher - Starting Out: The King's Indian",
                exercises: SAMPLE_PAGES
              };
            }
          }
          return b;
        });
      } catch (e) {
        console.error("Failed to parse saved books:", e);
      }
    }
    return [
      {
        id: 'book_1',
        title: "Joe Gallagher - Starting Out: The King's Indian",
        exercises: SAMPLE_PAGES
      }
    ];
  });

  const [selectedBookId, setSelectedBookId] = useState<string>(() => {
    return localStorage.getItem('chess_codex_selected_book_id_v2') || 'book_1';
  });

  // Calculate current book
  const currentBook = useMemo(() => {
    return books.find(b => b.id === selectedBookId) || books[0];
  }, [books, selectedBookId]);

  // Selected exercise ID
  const [selectedExerciseId, setSelectedExerciseId] = useState<string>(() => {
    const savedSelectedBookId = localStorage.getItem('chess_codex_selected_book_id_v2') || 'book_1';
    const initialBook = books.find(b => b.id === savedSelectedBookId) || books[0];
    return initialBook?.exercises[0]?.id || '';
  });

  // Calculate current active exercise
  const activeExercise = useMemo(() => {
    if (!currentBook) return null;
    return currentBook.exercises.find(e => e.id === selectedExerciseId) || currentBook.exercises[0] || null;
  }, [currentBook, selectedExerciseId]);

  const [activeGame, setActiveGame] = useState<ParsedChessGame>(() => {
    const savedSelectedBookId = localStorage.getItem('chess_codex_selected_book_id_v2') || 'book_1';
    const initialBook = books.find(b => b.id === savedSelectedBookId) || books[0];
    const initialExercise = initialBook?.exercises[0] || null;
    return initialExercise?.preparsedJson || SAMPLE_PAGES[0].preparsedJson;
  });

  const [currentMoveIndex, setCurrentMoveIndex] = useState<number>(-1); // -1 is start position

  // Opening Explainer States
  const [isExploringOpening, setIsExploringOpening] = useState<boolean>(false);
  const [currentOpeningMoveIndex, setCurrentOpeningMoveIndex] = useState<number>(-1);

  // Sideline Selection States
  const [activeSideline, setActiveSideline] = useState<SidelineVariation | null>(null);
  const [activeSidelineMoveIndex, setActiveSidelineMoveIndex] = useState<number>(-1);

  // Custom User Inputs
  const [pastedText, setPastedText] = useState<string>(SAMPLE_PAGES[0].textContext);
  const [uploadedImageBase64, setUploadedImageBase64] = useState<string | null>(null);
  const [uploadedImageName, setUploadedImageName] = useState<string | null>(null);
  const [pdfPageNumber, setPdfPageNumber] = useState<string>('1');

  // Full-book dynamic state
  const [fullBookTitleInput, setFullBookTitleInput] = useState<string>('');
  const [fullBookText, setFullBookText] = useState<string>('');
  const [uploadedFullBookFileBase64, setUploadedFullBookFileBase64] = useState<string | null>(null);
  const [uploadedFullBookFileName, setUploadedFullBookFileName] = useState<string | null>(null);
  const [isParsingFullBook, setIsParsingFullBook] = useState<boolean>(false);
  const [parseFullBookError, setParseFullBookError] = useState<string | null>(null);
  const [activeDigitizerMode, setActiveDigitizerMode] = useState<'single' | 'full'>('single');
  const [newBookTitle, setNewBookTitle] = useState<string>('');

  // Page range scanning and append modes
  const [fullBookStartPage, setFullBookStartPage] = useState<string>('12');
  const [fullBookEndPage, setFullBookEndPage] = useState<string>('20');
  const [importTargetMode, setImportTargetMode] = useState<'new' | 'append'>('append'); // default to append so they can easily fill books
  const [importTargetBookId, setImportTargetBookId] = useState<string>('');
  const [lastScannedPageInfo, setLastScannedPageInfo] = useState<{ start: string; end: string; bookId: string; bookTitle: string } | null>(null);
  const [parsingElapsedSeconds, setParsingElapsedSeconds] = useState<number>(0);
  const [parsingPhase, setParsingPhase] = useState<string>("Initializing parser stream connection...");

  useEffect(() => {
    if (books.length > 0 && !importTargetBookId) {
      setImportTargetBookId(books[0].id);
    }
  }, [books, importTargetBookId]);
  
  // Custom API configuration view
  const [systemPrompt, setSystemPrompt] = useState<string>(
    `You are an expert chess data parser. Your job is to take text or images from chess books and convert them into a structured JSON format.
Separated by moves, you must identify White and Black moves, the SAN notation, author's commentary, and compile it safely. 
Also look for alternative commentary variations in parentheses and extract them into the "sidelines" array according to the schema.`
  );

  // Interface States
  const [activeTab, setActiveTab] = useState<'learning' | 'games' | 'exercises' | 'digitizer' | 'json'>('learning');
  const [companionSectionTab, setCompanionSectionTab] = useState<'exercises' | 'illustrative'>('exercises');
  const [isParsing, setIsParsing] = useState<boolean>(false);
  const [parseError, setParseError] = useState<string | null>(null);
  const [copied, setCopied] = useState<boolean>(false);
  const [customJsonText, setCustomJsonText] = useState<string>('');
  const [fileHoverState, setFileHoverState] = useState<boolean>(false);

  // Auto-Play Timer
  const [isPlaying, setIsPlaying] = useState<boolean>(false);
  const [playbackSpeed, setPlaybackSpeed] = useState<number>(2000); // ms per move
  const autoPlayIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const opponentTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const [solitaireResetTrigger, setSolitaireResetTrigger] = useState<number>(0);
  const singleFileInputRef = useRef<HTMLInputElement>(null);
  const fullBookFileInputRef = useRef<HTMLInputElement>(null);

  // Narrative voicing toggle (speech synthesis)
  const [enableSpeech, setEnableSpeech] = useState<boolean>(false);

  // Solitaire Guess-the-Move Interactive Challenge States
  const [isCorrectionMode, setIsCorrectionMode] = useState<boolean>(false);
  const [solitairePlayer, setSolitairePlayer] = useState<'B' | 'W' | 'both' | 'auto'>('auto');
  const [solitaireStartFrom, setSolitaireStartFrom] = useState<'opening' | 'puzzle'>('opening');
  const [solitaireFrontierIndex, setSolitaireFrontierIndex] = useState<number>(-1);
  const [solitaireSidelineFrontierIndex, setSolitaireSidelineFrontierIndex] = useState<number>(-1);
  const [correctionFeedback, setCorrectionFeedback] = useState<{ text: string; isCorrect: boolean | null }>({
    text: 'Activate Interactive Solitaire Mode to test your chess depth directly on the board!',
    isCorrect: null
  });

  const openingMoves = useMemo(() => {
    return getOpeningMovesForPage(activeExercise);
  }, [activeExercise]);

  // Compile flat moves array for simpler navigation
  const gameMoves = useMemo(() => {
    const mainMoves = activeGame.interactive_section?.moves || [];
    return [...openingMoves, ...mainMoves];
  }, [openingMoves, activeGame]);

  // Compute exercises/games to render based on the active companion tab
  const exercisesToRender = useMemo(() => {
    if (!currentBook?.exercises) return [];
    return currentBook.exercises.filter(ex => {
      const isIllustrative = ex.id.startsWith('game_') && ex.id !== 'game_1_tactical_trap';
      return companionSectionTab === 'illustrative' ? isIllustrative : !isIllustrative;
    });
  }, [currentBook, companionSectionTab]);

  // Synchronize book list and selected ID
  useEffect(() => {
    localStorage.setItem(LOCAL_STORAGE_KEY, JSON.stringify(books));
  }, [books]);

  useEffect(() => {
    localStorage.setItem('chess_codex_selected_book_id_v2', selectedBookId);
  }, [selectedBookId]);

  // Global physical keyboard navigation hook
  useEffect(() => {
    const handleGlobalKeyDown = (e: KeyboardEvent) => {
      // Ignore if typing in text inputs or textareas
      const activeEl = document.activeElement?.tagName;
      if (activeEl === 'INPUT' || activeEl === 'TEXTAREA') return;

      if (e.key === 'ArrowLeft') {
        e.preventDefault();
        // Go back
        if (activeSideline) {
          if (activeSidelineMoveIndex > -1) {
            setActiveSidelineMoveIndex(prev => prev - 1);
          } else {
            // pivot back from sideline to main game
            setActiveSideline(null);
            // set main game to the starting move index of this sideline
            setCurrentMoveIndex(activeSideline.startingMoveIndex);
          }
        } else if (isExploringOpening) {
          if (currentOpeningMoveIndex > -1) {
            setCurrentOpeningMoveIndex(prev => prev - 1);
          }
        } else {
          if (currentMoveIndex > -1) {
            setCurrentMoveIndex(prev => prev - 1);
          }
        }
      } else if (e.key === 'ArrowRight') {
        e.preventDefault();
        // Go forward
        if (activeSideline) {
          const sldFrontier = solitaireSidelineFrontierIndex;
          if (isCorrectionMode) {
            if (activeSidelineMoveIndex < sldFrontier && activeSidelineMoveIndex < activeSideline.moves.length - 1) {
              setActiveSidelineMoveIndex(prev => prev + 1);
            }
          } else {
            if (activeSidelineMoveIndex < activeSideline.moves.length - 1) {
              setActiveSidelineMoveIndex(prev => prev + 1);
            }
          }
        } else if (isExploringOpening) {
          if (currentOpeningMoveIndex < openingMoves.length - 1) {
            setCurrentOpeningMoveIndex(prev => prev + 1);
          }
        } else {
          const mainFrontier = isCorrectionMode ? solitaireFrontierIndex : gameMoves.length - 1;
          if (currentMoveIndex < mainFrontier && currentMoveIndex < gameMoves.length - 1) {
            setCurrentMoveIndex(prev => prev + 1);
          }
        }
      }
    };

    window.addEventListener('keydown', handleGlobalKeyDown);
    return () => window.removeEventListener('keydown', handleGlobalKeyDown);
  }, [
    activeSideline, 
    activeSidelineMoveIndex, 
    isExploringOpening, 
    currentOpeningMoveIndex, 
    currentMoveIndex, 
    isCorrectionMode, 
    solitaireFrontierIndex, 
    solitaireSidelineFrontierIndex, 
    gameMoves.length, 
    openingMoves.length
  ]);

  // Synchronize state when activeExercise changes
  useEffect(() => {
    if (activeExercise) {
      if (opponentTimeoutRef.current) {
        clearTimeout(opponentTimeoutRef.current);
        opponentTimeoutRef.current = null;
      }
      setActiveGame(activeExercise.preparsedJson);
      setPastedText(activeExercise.textContext);
      setUploadedImageBase64(null);
      setUploadedImageName(null);
      setCurrentMoveIndex(-1);
      setActiveSideline(null);
      setActiveSidelineMoveIndex(-1);
      setIsPlaying(false);
      setIsCorrectionMode(false);
      setIsExploringOpening(false);
      setCurrentOpeningMoveIndex(-1);
      setCorrectionFeedback({
        text: 'Activate Interactive Solitaire Mode to test your chess depth directly on the board!',
        isCorrect: null
      });

      // Automatically sync layout companion category tab match
      const isIllustrative = activeExercise.id.startsWith('game_') && activeExercise.id !== 'game_1_tactical_trap';
      setCompanionSectionTab(isIllustrative ? 'illustrative' : 'exercises');
    }
  }, [activeExercise]);

  const initializeSolitaire = (playerRole: 'W' | 'B' | 'both' | 'auto') => {
    setIsPlaying(false);
    setIsCorrectionMode(true);
    setSolitairePlayer(playerRole);

    if (opponentTimeoutRef.current) {
      clearTimeout(opponentTimeoutRef.current);
      opponentTimeoutRef.current = null;
    }

    if (gameMoves.length === 0) {
      setCorrectionFeedback({
        text: "No moves loaded for this game to play Solitaire Mode.",
        isCorrect: null
      });
      return;
    }

    const interactiveStartIndex = solitaireStartFrom === 'opening' ? 0 : openingMoves.length;
    setSolitaireSidelineFrontierIndex(-1);

    let resolvedRole: 'W' | 'B' | 'both' = playerRole === 'auto'
      ? (gameMoves[interactiveStartIndex]?.player || 'W')
      : playerRole;

    if (resolvedRole === 'B') {
      // Find first Black move in the interactive puzzle section
      let firstBlackIdx = gameMoves.findIndex((m, index) => index >= interactiveStartIndex && m.player === 'B');
      if (firstBlackIdx === -1) {
        firstBlackIdx = gameMoves.findIndex(m => m.player === 'B');
      }
      if (firstBlackIdx !== -1) {
        // Set board state to just before Black's move
        setCurrentMoveIndex(firstBlackIdx - 1);
        setSolitaireFrontierIndex(firstBlackIdx - 1);
        
        if (firstBlackIdx > 0) {
          const prevMove = gameMoves[firstBlackIdx - 1];
          setCorrectionFeedback({
            text: `Opponent played White's move: ${prevMove.move_number}.${prevMove.player === 'B' ? '..' : ''} ${prevMove.move}. What should Black respond with? Drag or click a piece to try!`,
            isCorrect: null
          });
          triggerVoiceSynthesis(`Opponent played ${prevMove.move}. What is Black's play?`);
        } else {
          // Black plays from the very start
          setCorrectionFeedback({
            text: `It is Black's turn from the start of this section! Play Black's first move: ${gameMoves[0].move_number}... ${gameMoves[0].move}? Drag or click a piece to try!`,
            isCorrect: null
          });
          triggerVoiceSynthesis(`It is Black's turn from the start. What is Black's move?`);
        }
      } else {
        setCurrentMoveIndex(-1);
        setSolitaireFrontierIndex(-1);
        setCorrectionFeedback({
          text: `No of Black's moves found in this line. Try guessing from the start!`,
          isCorrect: null
        });
      }
    } else if (playerRole === 'W') {
      // Find first White move in the interactive puzzle section
      let firstWhiteIdx = gameMoves.findIndex((m, index) => index >= interactiveStartIndex && m.player === 'W');
      if (firstWhiteIdx === -1) {
        firstWhiteIdx = gameMoves.findIndex(m => m.player === 'W');
      }
      if (firstWhiteIdx !== -1) {
        setCurrentMoveIndex(firstWhiteIdx - 1);
        setSolitaireFrontierIndex(firstWhiteIdx - 1);
        
        if (firstWhiteIdx > 0) {
          const prevMove = gameMoves[firstWhiteIdx - 1];
          setCorrectionFeedback({
            text: `Opponent played Black's move: ${prevMove.move_number}.${prevMove.player === 'B' ? '..' : ''} ${prevMove.move}. What should White respond with? Drag or click a piece to try!`,
            isCorrect: null
          });
          triggerVoiceSynthesis(`Opponent played ${prevMove.move}. What is White's play?`);
        } else {
          // White plays from the start
          setCorrectionFeedback({
            text: `It is White's turn from the start of this section! Play White's first move: ${gameMoves[0].move_number}. ${gameMoves[0].move}? Drag or click a piece to try!`,
            isCorrect: null
          });
          triggerVoiceSynthesis(`It is White's turn from the start. What is White's move?`);
        }
      } else {
        setCurrentMoveIndex(-1);
        setSolitaireFrontierIndex(-1);
        setCorrectionFeedback({
          text: `No of White's moves found in this line. Try guessing from the start!`,
          isCorrect: null
        });
      }
    } else {
      // Guess all moves
      setCurrentMoveIndex(-1);
      setSolitaireFrontierIndex(-1);
      const firstMove = gameMoves[0];
      setCorrectionFeedback({
        text: `Guess every single move! What should ${firstMove.player === 'W' ? 'White' : 'Black'} play first: Move ${firstMove.move_number}${firstMove.player === 'W' ? '.' : '...'}?`,
        isCorrect: null
      });
      triggerVoiceSynthesis(`Guess every move. What should ${firstMove.player === 'W' ? 'White' : 'Black'} play first?`);
    }
  };

  const resetSolitaire = () => {
    if (opponentTimeoutRef.current) {
      clearTimeout(opponentTimeoutRef.current);
      opponentTimeoutRef.current = null;
    }
    setSolitaireResetTrigger(prev => prev + 1);
    initializeSolitaire(solitairePlayer);
  };

  // Trigger immediate board re-init when changing starting bounds
  useEffect(() => {
    if (isCorrectionMode) {
      resetSolitaire();
    }
  }, [solitaireStartFrom]);

  const toggleCorrectionMode = (enable: boolean) => {
    if (enable) {
      resetSolitaire();
    } else {
      if (opponentTimeoutRef.current) {
        clearTimeout(opponentTimeoutRef.current);
        opponentTimeoutRef.current = null;
      }
      setIsCorrectionMode(false);
      setCorrectionFeedback({
        text: 'Activate Interactive Solitaire Mode to test your chess depth directly on the board!',
        isCorrect: null
      });
    }
  };

  const handleCorrectMovePlay = (nextIdx: number) => {
    const isSideline = !!activeSideline;
    const movesList = isSideline ? activeSideline.moves : gameMoves;

    if (isSideline) {
      setActiveSidelineMoveIndex(nextIdx);
      setSolitaireSidelineFrontierIndex(nextIdx);
    } else {
      setCurrentMoveIndex(nextIdx);
      setSolitaireFrontierIndex(nextIdx);
    }
    
    const correctMove = movesList[nextIdx];
    let commentary = correctMove.commentary || "Excellent! That is the correct book move.";
    
    setCorrectionFeedback({
      text: `CORRECT: Played ${correctMove.move}. ${commentary}`,
      isCorrect: true
    });

    triggerVoiceSynthesis(commentary);

    // Dynamic AI auto-response check
    let resolvedRole = solitairePlayer;
    if (solitairePlayer === 'auto') {
      const activePuzzleMoves = isSideline ? activeSideline.moves : gameMoves.slice(solitaireStartFrom === 'puzzle' ? openingMoves.length : 0);
      resolvedRole = activePuzzleMoves[0]?.player || 'W';
    }

    const isPlayingAsBlackOnly = resolvedRole === 'B';
    const isPlayingAsWhiteOnly = resolvedRole === 'W';
    
    const hasMoreMoves = nextIdx + 1 < movesList.length;
    if (hasMoreMoves) {
      const nextOpponentMove = movesList[nextIdx + 1];
      
      const machineNeedsToPlay = 
        (isPlayingAsBlackOnly && nextOpponentMove.player === 'W') ||
        (isPlayingAsWhiteOnly && nextOpponentMove.player === 'B');
        
      if (machineNeedsToPlay) {
        // Wait 1200ms and make opponent response
        if (opponentTimeoutRef.current) clearTimeout(opponentTimeoutRef.current);
        opponentTimeoutRef.current = setTimeout(() => {
          if (isSideline) {
            setActiveSidelineMoveIndex(nextIdx + 1);
            setSolitaireSidelineFrontierIndex(nextIdx + 1);
          } else {
            setCurrentMoveIndex(nextIdx + 1);
            setSolitaireFrontierIndex(nextIdx + 1);
          }
          const oppReply = movesList[nextIdx + 1];
          const playerNextIdx = nextIdx + 2;
          
          if (playerNextIdx < movesList.length) {
            const userNextMove = movesList[playerNextIdx];
            setCorrectionFeedback(prev => ({
              text: `Opponent answered with ${oppReply.move}. Now, what should ${userNextMove.player === 'W' ? 'White' : 'Black'} play on move ${userNextMove.move_number}?`,
              isCorrect: null
            }));
            triggerVoiceSynthesis(`Opponent replied ${oppReply.move}. What's your move next?`);
          } else {
            setCorrectionFeedback({
              text: `Opponent answered with ${oppReply.move}. This alternative variation is complete! Splendid chess foresight!`,
              isCorrect: true
            });
            triggerVoiceSynthesis(`Opponent played ${oppReply.move}. This variation is complete.`);
          }
          opponentTimeoutRef.current = null;
        }, 1250);
      } else {
        // Guessing both sides, prompt next
        const userNextMove = movesList[nextIdx + 1];
        if (opponentTimeoutRef.current) clearTimeout(opponentTimeoutRef.current);
        opponentTimeoutRef.current = setTimeout(() => {
          setCorrectionFeedback({
            text: `Excellent. Now guess the reply for ${userNextMove.player === 'W' ? 'White' : 'Black'}: Move ${userNextMove.move_number}${userNextMove.player === 'W' ? '.' : '...'}`,
            isCorrect: null
          });
          triggerVoiceSynthesis(`Now guess the play for ${userNextMove.player === 'W' ? 'White' : 'Black'}.`);
          opponentTimeoutRef.current = null;
        }, 1000);
      }
    } else {
      setCorrectionFeedback({
        text: isSideline 
          ? `Incredible! You have successfully completed this entire alternative sideline variation: "${activeSideline.name}"!`
          : "Incredible! You have successfully completed the entire line written in the chess codex!",
        isCorrect: true
      });
      triggerVoiceSynthesis(isSideline 
        ? `Incredible! You completed the variation ${activeSideline.name}.`
        : "Incredible! You have completed the entire line written in the chess codex!");
    }
  };

  const handleAlternateSidelinePlayed = (sld: SidelineVariation) => {
    setActiveSideline(sld);
    setActiveSidelineMoveIndex(0);
    setSolitaireSidelineFrontierIndex(0);

    const correctMove = sld.moves[0];
    const commentary = correctMove.commentary || sld.description || "Entering alternative route.";

    setCorrectionFeedback({
      text: `ALT ROUTE BRANCHED: Played ${correctMove.move}, pivoting smoothly to sideline: "${sld.name}". ${commentary}`,
      isCorrect: true
    });

    triggerVoiceSynthesis(`Alternative route entered: ${sld.name}. ${commentary}`);

    // Dynamic AI opponent response inside the newly entered sideline
    let resolvedRole = solitairePlayer;
    if (solitairePlayer === 'auto') {
      resolvedRole = sld.moves[0]?.player || 'W';
    }
    const isPlayingAsBlackOnly = resolvedRole === 'B';
    const isPlayingAsWhiteOnly = resolvedRole === 'W';

    const hasMoreMoves = sld.moves.length > 1;
    if (hasMoreMoves) {
      const nextOpponentMove = sld.moves[1];
      const machineNeedsToPlay = 
        (isPlayingAsBlackOnly && nextOpponentMove.player === 'W') ||
        (isPlayingAsWhiteOnly && nextOpponentMove.player === 'B');

      if (machineNeedsToPlay) {
        if (opponentTimeoutRef.current) clearTimeout(opponentTimeoutRef.current);
        opponentTimeoutRef.current = setTimeout(() => {
          setActiveSidelineMoveIndex(1);
          setSolitaireSidelineFrontierIndex(1);
          const oppReply = sld.moves[1];
          const playerNextIdx = 2;

          if (playerNextIdx < sld.moves.length) {
            const userNextMove = sld.moves[playerNextIdx];
            setCorrectionFeedback(prev => ({
              text: `Entered sideline: "${sld.name}". Opponent answered with ${oppReply.move}. Now, what should ${userNextMove.player === 'W' ? 'White' : 'Black'} play on move ${userNextMove.move_number}?`,
              isCorrect: null
            }));
            triggerVoiceSynthesis(`Opponent replied ${oppReply.move}. What's your next move in this sideline?`);
          } else {
            setCorrectionFeedback({
              text: `Entered sideline: "${sld.name}". Opponent answered with ${oppReply.move}. This alternative variation is complete!`,
              isCorrect: true
            });
            triggerVoiceSynthesis(`Opponent played ${oppReply.move}. This variation is complete.`);
          }
          opponentTimeoutRef.current = null;
        }, 1250);
      } else {
        const userNextMove = sld.moves[1];
        if (opponentTimeoutRef.current) clearTimeout(opponentTimeoutRef.current);
        opponentTimeoutRef.current = setTimeout(() => {
          setCorrectionFeedback({
            text: `Entered sideline: "${sld.name}". Now guess the reply for ${userNextMove.player === 'W' ? 'White' : 'Black'}: Move ${userNextMove.move_number}${userNextMove.player === 'W' ? '.' : '...'}`,
            isCorrect: null
          });
          triggerVoiceSynthesis(`Guess the reply in this sideline.`);
          opponentTimeoutRef.current = null;
        }, 1000);
      }
    } else {
      setCorrectionFeedback({
        text: `Incredible! Played ${correctMove.move}, completing alternative sideline variation: "${sld.name}"!`,
        isCorrect: true
      });
      triggerVoiceSynthesis(`Completed sideline variation: ${sld.name}`);
    }
  };

  const handleIncorrectMovePlay = (playedSAN: string, expectedSAN: string) => {
    if (activeSideline) {
      if (expectedSAN === 'none' || expectedSAN === '') {
        setCorrectionFeedback({
          text: `You completed this sideline, but tried playing ${playedSAN}. Excellent chess depth!`,
          isCorrect: null
        });
      } else {
        setCorrectionFeedback({
          text: `Not quite! Tried ${playedSAN} inside the alternative variation, but the book suggests ${expectedSAN}. Study the position and try again!`,
          isCorrect: false
        });
        triggerVoiceSynthesis(`Not quite inside alternative variation! The book suggests ${expectedSAN}. Try again.`);
      }
      return;
    }

    // Check if the expected move is 'b5' (specifically from the Gallgher book page)
    const normalizedExpected = expectedSAN.replace(/[!?#+$]+$/, '');
    if (normalizedExpected === 'b5') {
      setCorrectionFeedback({
        text: "Not quite! The book suggests b5 to start hitting the knight on c4. Try again!",
        isCorrect: false
      });
      triggerVoiceSynthesis("Not quite! The book suggests b5 to start hitting the knight on c4. Try again!");
    } else {
      setCorrectionFeedback({
        text: `Not quite! Tried ${playedSAN}, but the book suggests ${expectedSAN}. Study the position and try again!`,
        isCorrect: false
      });
      triggerVoiceSynthesis(`Not quite! The book suggests ${expectedSAN}. Try again.`);
    }
  };

  // Helper to compile main-line initial setup up to the sideline divergence point
  const getSidelinePrefixInitialMoves = (sideline: SidelineVariation): string => {
    const prefixMoves = gameMoves.slice(0, openingMoves.length + sideline.startingMoveIndex + 1);
    let movesStr = '';
    prefixMoves.forEach(m => {
      movesStr += ' ' + m.move;
    });
    return movesStr.trim();
  };

  // Keep JSON string state in sync with current chess game structure
  useEffect(() => {
    setCustomJsonText(JSON.stringify(activeGame, null, 2));
  }, [activeGame]);

  // Read current commentary aloud if feedback is enabled
  const triggerVoiceSynthesis = (text: string) => {
    if (!enableSpeech || !text) return;
    try {
      window.speechSynthesis.cancel(); // Stop anything playing
      const utterance = new SpeechSynthesisUtterance(text);
      utterance.rate = 1.1;
      utterance.pitch = 1.0;
      window.speechSynthesis.speak(utterance);
    } catch (e) {
      console.warn("Speech synthesis unavailable", e);
    }
  };

  // Sync commentary reads with move transitions
  useEffect(() => {
    let commentary = '';
    if (activeSideline) {
      if (activeSidelineMoveIndex >= 0 && activeSideline.moves[activeSidelineMoveIndex]) {
        commentary = activeSideline.moves[activeSidelineMoveIndex].commentary || '';
      } else {
        commentary = activeSideline.description;
      }
    } else if (isExploringOpening) {
      if (currentOpeningMoveIndex >= 0 && openingMoves[currentOpeningMoveIndex]) {
        commentary = openingMoves[currentOpeningMoveIndex].commentary || '';
      } else {
        commentary = "Opening Setup Explainer is active. Use the navigation buttons or click on any moves to understand the setup ideas.";
      }
    } else {
      if (currentMoveIndex >= 0 && gameMoves[currentMoveIndex]) {
        commentary = gameMoves[currentMoveIndex].commentary || '';
      }
    }
    if (commentary) {
      triggerVoiceSynthesis(commentary);
    }
  }, [currentMoveIndex, activeSidelineMoveIndex, activeSideline, isExploringOpening, currentOpeningMoveIndex, openingMoves, enableSpeech]);

  // Handle Autoplay Cycles
  useEffect(() => {
    if (isPlaying) {
      autoPlayIntervalRef.current = setInterval(() => {
        if (isExploringOpening) {
          setCurrentOpeningMoveIndex(prev => {
            if (prev >= openingMoves.length - 1) {
              setIsPlaying(false);
              return prev;
            }
            return prev + 1;
          });
        } else {
          setCurrentMoveIndex(prev => {
            if (prev >= gameMoves.length - 1) {
              setIsPlaying(false);
              return prev;
            }
            return prev + 1;
          });
        }
      }, playbackSpeed);
    } else {
      if (autoPlayIntervalRef.current) {
        clearInterval(autoPlayIntervalRef.current);
      }
    }

    return () => {
      if (autoPlayIntervalRef.current) {
        clearInterval(autoPlayIntervalRef.current);
      }
    };
  }, [isPlaying, gameMoves.length, openingMoves.length, isExploringOpening, playbackSpeed]);

  // Clean up opponent response timeout on unmount
  useEffect(() => {
    return () => {
      if (opponentTimeoutRef.current) {
        clearTimeout(opponentTimeoutRef.current);
      }
    };
  }, []);

  // Handle Single Page uploads (images or PDF)
  const handleSinglePageFile = (file: File) => {
    const isImage = file.type.startsWith('image/');
    const isPdf = file.type === 'application/pdf';
    
    if (!isImage && !isPdf && !file.name.endsWith('.pdf')) {
      showAlert('Please select a valid image or PDF file of a chess book page.', 'error');
      return;
    }
    setUploadedImageName(file.name);
    
    const reader = new FileReader();
    reader.onload = () => {
      setUploadedImageBase64(reader.result as string);
    };
    reader.readAsDataURL(file);
  };

  const handleFullBookFile = (file: File) => {
    const isPdf = file.type === 'application/pdf';
    const isImage = file.type.startsWith('image/');
    const isText = file.type.startsWith('text/') || file.name.endsWith('.txt') || file.name.endsWith('.pgn');
    
    if (!isPdf && !isImage && !isText && !file.name.endsWith('.pdf')) {
      showAlert('Please select a valid PDF, image, or text file of a chess book.', 'error');
      return;
    }
    setUploadedFullBookFileName(file.name);
    
    const reader = new FileReader();
    reader.onload = () => {
      setUploadedFullBookFileBase64(reader.result as string);
    };
    reader.readAsDataURL(file);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setFileHoverState(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleSinglePageFile(e.dataTransfer.files[0]);
    }
  };

  // POST Request to call server-side Gemini API Parser
  const parseChessPage = async () => {
    // If previous parsing is active, abort it
    if (singlePageAbortControllerRef.current) {
      singlePageAbortControllerRef.current.abort();
    }
    const controller = new AbortController();
    singlePageAbortControllerRef.current = controller;

    setIsParsing(true);
    setParseError(null);
    setCurrentMoveIndex(-1);
    
    try {
      const payload: any = {
        customPrompt: systemPrompt
      };

      if (uploadedImageBase64) {
        payload.image = uploadedImageBase64;
        if (uploadedImageName?.toLowerCase().endsWith('.pdf')) {
          payload.pdfPage = pdfPageNumber;
        }
      }
      if (pastedText && pastedText.trim()) {
        payload.text = pastedText;
      }

      const res = await fetch('/api/parse-chess', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(payload),
        signal: controller.signal
      });

      const data = await res.json();

      if (!res.ok) {
        throw new Error(data.error || 'Server parsing request failed.');
      }

      // Check structure sanity
      if (!data.interactive_section || !data.interactive_section.moves) {
        throw new Error("Gemini completed successfully but parsed layout is missing the required moves list structure. Try refining your text or prompting.");
      }

      // Populate new parsed game
      const parsedGame: ParsedChessGame = data;
      const newExerciseId = `exc_${Date.now()}`;
      
      const newExercise: SampleBookPage = {
        id: newExerciseId,
        title: `${parsedGame.white || 'White'} vs ${parsedGame.black || 'Black'} (${parsedGame.event || 'Digitized'})`,
        description: `Digitized chess board scenario.`,
        imageFilename: uploadedImageName || 'digitized_upload.jpg',
        textContext: pastedText || 'Pasted transcription text.',
        preparsedJson: parsedGame
      };

      setBooks(prev => prev.map(b => {
        if (b.id === selectedBookId) {
          return {
            ...b,
            exercises: [...b.exercises, newExercise]
          };
        }
        return b;
      }));

      setSelectedExerciseId(newExerciseId);
      setActiveGame(parsedGame);
      setCustomJsonText(JSON.stringify(parsedGame, null, 2));
      showAlert("Successfully digitized chess page and added to library!", "success");
      setActiveTab('learning'); // Switch back to see result!
      
    } catch (err: any) {
      if (err.name === 'AbortError') {
        setParseError('Compilation/parsing cancelled by user.');
        return;
      }
      console.error(err);
      setParseError(err.message || 'Error occurred while contacting Gemini Parser model.');
    } finally {
      setIsParsing(false);
      if (singlePageAbortControllerRef.current === controller) {
        singlePageAbortControllerRef.current = null;
      }
    }
  };

  const importFullBook = async () => {
    if (!fullBookText.trim() && !uploadedFullBookFileBase64) {
      showAlert("Please either paste chapters text or upload a book file (PDF, image, or text).", "error");
      return;
    }
    if (fullBookAbortControllerRef.current) {
      fullBookAbortControllerRef.current.abort();
    }
    const controller = new AbortController();
    fullBookAbortControllerRef.current = controller;

    setIsParsingFullBook(true);
    setParseFullBookError(null);
    setParsingElapsedSeconds(0);
    setParsingPhase("⏳ Initializing pipeline and uploading document bytes...");

    const progressPhases = [
      { maxSec: 4, text: "⏳ Connecting to deep multimodal Gemini parsing pipeline..." },
      { maxSec: 10, text: "📖 Scanning selected PDF pages. Fetching OCR text context and image components..." },
      { maxSec: 17, text: "🎨 Transcribing chess diagrams, coordinate grids, and piece positions..." },
      { maxSec: 25, text: "📝 Deciphering Move notation symbols (e.g. Nf3, d5, O-O) and key sidelines commentary..." },
      { maxSec: 36, text: "🔀 Compiling multiple games, openings, and chapter sections logically..." },
      { maxSec: 48, text: "⚙️ Encoding commentary annotations and board state positions into interactive chess.js PGN schemas..." },
      { maxSec: 62, text: "⚡ Structuring parenthetical comment lines and variations commentary tree..." },
      { maxSec: 80, text: "💎 Polishing board vectors, starting configurations, and player credits..." },
      { maxSec: 105, text: "⌛ Still compiling! Larger page ranges take longer to structure. We are formatting the final interactive codex object..." },
      { maxSec: 9999, text: "🚀 Running final sanity schema checks. Completing compilation. Stand by..." }
    ];

    let seconds = 0;
    const interval = setInterval(() => {
      seconds += 1;
      setParsingElapsedSeconds(seconds);
      const phase = progressPhases.find(p => seconds <= p.maxSec);
      if (phase) {
        setParsingPhase(phase.text);
      }
    }, 1000);

    try {
      const payload: any = {
        customPrompt: `You are an expert chess data parser specializing in books.
Parse all instructions, chess games, diagrams, commentaries, and sidelines. Reformat the book content into the precise JSON structure.`
      };

      if (fullBookText.trim()) {
        payload.text = fullBookText;
      }
      if (uploadedFullBookFileBase64) {
        payload.file = uploadedFullBookFileBase64;
        if (uploadedFullBookFileName?.toLowerCase().endsWith('.pdf')) {
          payload.pdfStartPage = fullBookStartPage;
          payload.pdfEndPage = fullBookEndPage;
        }
      }

      const res = await fetch('/api/parse-book', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(payload),
        signal: controller.signal
      });
      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.error || "Failed to process the book with Gemini.");
      }
      
      const finalBookTitle = fullBookTitleInput.trim() ? fullBookTitleInput.trim() : (data.book_title || "My Brand-New Digitized Book");
      
      if (!data.exercises || !Array.isArray(data.exercises) || data.exercises.length === 0) {
        throw new Error("No games/exercises parsed inside the book. Please make sure the book content contains sequential positions or lists of moves.");
      }

      const formattedExercises: SampleBookPage[] = data.exercises.map((ex: any, idx: number) => ({
        id: ex.id || `exc_${Date.now()}_${idx}`,
        title: ex.title || `Exercise ${idx + 1}: ${ex.preparsedJson?.white || 'White'} vs ${ex.preparsedJson?.black || 'Black'}`,
        description: ex.description || `Tactical chess fragment #${idx + 1}`,
        imageFilename: 'embedded_illustration.jpg',
        textContext: ex.textContext || 'Parsed chess book chapters.',
        preparsedJson: ex.preparsedJson
      }));

      let nextBookId = importTargetBookId;

      if (importTargetMode === 'append' && importTargetBookId) {
        setBooks(prev => prev.map(b => {
          if (b.id === importTargetBookId) {
            return {
              ...b,
              exercises: [...b.exercises, ...formattedExercises]
            };
          }
          return b;
        }));
        setSelectedBookId(importTargetBookId);
        if (formattedExercises.length > 0) {
          setSelectedExerciseId(formattedExercises[0].id);
        }
        showAlert(`Flawlessly appended ${formattedExercises.length} fully interactive exercises/games directly into your active book: "${books.find(b => b.id === importTargetBookId)?.title || 'Target Book'}"!`, 'success');
      } else {
        const generatedId = `book_${Date.now()}`;
        nextBookId = generatedId;
        const newBook: ChessBook = {
          id: generatedId,
          title: finalBookTitle,
          exercises: formattedExercises
        };
        setBooks(prev => [...prev, newBook]);
        setSelectedBookId(newBook.id);
        if (newBook.exercises.length > 0) {
          setSelectedExerciseId(newBook.exercises[0].id);
        }
        // Auto select this newly created book for subsequent appends
        setImportTargetBookId(generatedId);
        setImportTargetMode('append');
        showAlert(`Flawlessly imported "${newBook.title}" as a brand-new book with ${newBook.exercises.length} fully interactive exercises!`, 'success');
      }

      // Record what page range was successfully completed and auto-increment bounds
      if (uploadedFullBookFileName?.toLowerCase().endsWith('.pdf')) {
        const startVal = parseInt(fullBookStartPage, 10);
        const endVal = parseInt(fullBookEndPage, 10);
        if (!isNaN(startVal) && !isNaN(endVal)) {
          const pageSize = endVal - startVal + 1;
          const nextStart = endVal + 1;
          const nextEnd = endVal + (pageSize > 0 ? pageSize : 8);
          
          setLastScannedPageInfo({
            start: fullBookStartPage,
            end: fullBookEndPage,
            bookId: nextBookId,
            bookTitle: finalBookTitle
          });
          
          // Auto advance to the next logical chunk
          setFullBookStartPage(nextStart.toString());
          setFullBookEndPage(nextEnd.toString());
        }
      }

      setActiveTab('learning');
      setFullBookText('');
      setFullBookTitleInput('');
      // Do NOT clear uploadedFullBookFileBase64 and uploadedFullBookFileName so they can scan consecutive ranges without re-uploading!
    } catch (e: any) {
      if (e.name === 'AbortError') {
        setParseFullBookError("Compilation cancelled by user.");
        return;
      }
      console.error(e);
      setParseFullBookError(e.message || "Failed to parse book.");
    } finally {
      setIsParsingFullBook(false);
      clearInterval(interval);
      if (fullBookAbortControllerRef.current === controller) {
        fullBookAbortControllerRef.current = null;
      }
    }
  };

  const createEmptyBook = () => {
    if (!newBookTitle.trim()) {
      showAlert("Please provide a book title.", "error");
      return;
    }
    const newBook: ChessBook = {
      id: `book_${Date.now()}`,
      title: newBookTitle.trim(),
      exercises: []
    };
    setBooks(prev => [...prev, newBook]);
    setSelectedBookId(newBook.id);
    setSelectedExerciseId('');
    setNewBookTitle('');
    showAlert(`Successfully created an empty book "${newBook.title}"! You can now add individual exercises using the Single Page Digitizer.`, "success");
  };

  const deleteCurrentBook = () => {
    if (books.length <= 1) {
      showAlert("Cannot delete the last remaining book in your collection.", "error");
      return;
    }
    showConfirm(
      `Are you sure you want to delete "${currentBook.title}" and all its ${currentBook.exercises.length} exercises? This action is irreversible.`,
      () => {
        const remainingBooks = books.filter(b => b.id !== currentBook.id);
        setBooks(remainingBooks);
        const nextBook = remainingBooks[0];
        setSelectedBookId(nextBook.id);
        setSelectedExerciseId(nextBook.exercises[0]?.id || '');
        showAlert("Selected book has been deleted successfully.", "info");
      }
    );
  };

  const restoreDefaultSampleBook = () => {
    showConfirm(
      'This will reset "Joe Gallagher - Starting Out: The King\'s Indian" to the official starting playbook with all 68 illustrative games. Your custom changes to this specific book will be reset. Proceed?',
      () => {
        setBooks(prev => {
          const filtered = prev.filter(b => b.id !== 'book_1');
          const defaultBook: ChessBook = {
            id: 'book_1',
            title: "Joe Gallagher - Starting Out: The King's Indian",
            exercises: SAMPLE_PAGES
          };
          return [defaultBook, ...filtered];
        });
        setSelectedBookId('book_1');
        setSelectedExerciseId(SAMPLE_PAGES[0].id);
        showAlert("Successfully restored/reset the official volume with all 68 illustrative games!", "success");
      }
    );
  };

  // Apply real-time edits to the raw JSON editor
  const applyJsonChanges = () => {
    try {
      const parsed = JSON.parse(customJsonText);
      if (!parsed.interactive_section || !parsed.interactive_section.moves) {
        showAlert("Warning: JSON structure must contain a valid 'interactive_section' and 'moves' array.", "error");
        return;
      }
      setActiveGame(parsed);
      setCurrentMoveIndex(-1);

      // Save changes back to our library/books state
      setBooks(prev => prev.map(bk => {
        if (bk.id === selectedBookId) {
          return {
            ...bk,
            exercises: bk.exercises.map(ex => {
              if (ex.id === selectedExerciseId) {
                return { ...ex, preparsedJson: parsed };
              }
              return ex;
            })
          };
        }
        return bk;
      }));

      showAlert("Successfully applied your raw JSON schema edits to the chess board and saved to the book library!", "success");
    } catch (e: any) {
      showAlert(`Invalid JSON format: ${e.message}`, "error");
    }
  };

  const handleCopyToClipboard = () => {
    navigator.clipboard.writeText(customJsonText);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="min-h-screen bg-[#F9F7F2] text-[#1A1A1A] font-sans antialiased overflow-x-hidden flex flex-col selection:bg-red-700/10 selection:text-[#1A1A1A]">
      
      {/* Main Editorial Header */}
      <header className="flex flex-col md:flex-row md:items-center justify-between px-6 lg:px-12 py-6 border-b border-black/10 bg-[#FAF8F5]">
        <div className="flex flex-col sm:flex-row sm:items-baseline gap-4 text-left">
          <h1 className="text-4xl font-serif font-light tracking-tight italic text-[#1A1A1A]">Chess Codex</h1>
          <span className="text-[10px] font-sans uppercase tracking-[0.2em] opacity-60">Interactive Playbook</span>
        </div>
        
        <div className="flex flex-wrap items-center gap-3 mt-4 md:mt-0 justify-end">
          {/* Current Book Selection */}
          <div className="flex items-center gap-2 bg-[#F9F7F2] border border-black/10 rounded px-3 py-1.5 text-xs">
            <span className="text-[9px] font-sans uppercase tracking-widest opacity-60 font-bold text-[#1A1A1A]">Book:</span>
            <select
              value={selectedBookId}
              onChange={(e) => {
                const bookId = e.target.value;
                setSelectedBookId(bookId);
                const book = books.find(b => b.id === bookId);
                if (book && book.exercises.length > 0) {
                  setSelectedExerciseId(book.exercises[0].id);
                } else {
                  setSelectedExerciseId('');
                }
              }}
              className="bg-transparent border-0 text-xs text-[#1A1A1A] outline-none cursor-pointer focus:ring-0 font-serif font-medium max-w-[160px] sm:max-w-[220px] truncate"
            >
              {books.map(b => (
                <option key={b.id} value={b.id} className="bg-[#FAF8F5] text-[#1A1A1A]">
                  {b.title}
                </option>
              ))}
            </select>

            {/* Quick delete for any book if multiple exist in library */}
            {books.length > 1 && (
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
                  e.preventDefault();
                  deleteCurrentBook();
                }}
                className="text-stone-400 hover:text-red-600 transition-colors ml-2 p-1 cursor-pointer flex items-center justify-center shrink-0"
                title="Delete this book"
              >
                <Trash2 size={13} className="shrink-0 pointer-events-none" />
              </button>
            )}
          </div>
        </div>
      </header>

      {/* Navigation Sub-header / Tabs */}
      <div className="bg-[#141414] text-white px-6 lg:px-12 py-3 border-b border-white/10 flex flex-wrap items-center justify-between gap-4">
        <nav className="flex flex-wrap gap-6 text-[11px] font-sans uppercase tracking-[0.2em]">
          <button
            onClick={() => setActiveTab('learning')}
            className={`pb-1 transition-all flex items-center gap-1.5 cursor-pointer ${
              activeTab === 'learning' 
                ? 'border-b-2 border-[#D97706] text-[#D97706] font-bold' 
                : 'opacity-65 text-gray-300 hover:opacity-100 hover:text-white'
            }`}
          >
            <BookOpen size={13} />
            <span>🎓 Learn Openings</span>
          </button>
          <button
            onClick={() => setActiveTab('games')}
            className={`pb-1 transition-all flex items-center gap-1.5 cursor-pointer ${
              activeTab === 'games' 
                ? 'border-b-2 border-[#D97706] text-[#D97706] font-bold' 
                : 'opacity-65 text-gray-300 hover:opacity-100 hover:text-white'
            }`}
          >
            <Trophy size={13} />
            <span>📚 Illustrative Games</span>
          </button>
          <button
            onClick={() => setActiveTab('exercises')}
            className={`pb-1 transition-all flex items-center gap-1.5 cursor-pointer ${
              activeTab === 'exercises' 
                ? 'border-b-2 border-[#D97706] text-[#D97706] font-bold' 
                : 'opacity-65 text-gray-300 hover:opacity-100 hover:text-white'
            }`}
          >
            <Sparkles size={13} />
            <span>🎯 Tactical Quiz</span>
          </button>
          <button
            onClick={() => setActiveTab('digitizer')}
            className={`pb-1 transition-all flex items-center gap-1.5 cursor-pointer ${
              activeTab === 'digitizer' 
                ? 'border-b-2 border-[#D97706] text-[#D97706] font-bold' 
                : 'opacity-65 text-gray-300 hover:opacity-100 hover:text-white'
            }`}
          >
            <Upload size={13} />
            <span>⚡ Digitizer AI</span>
          </button>
          <button
            onClick={() => setActiveTab('json')}
            className={`pb-1 transition-all flex items-center gap-1.5 cursor-pointer ${
              activeTab === 'json' 
                ? 'border-b-2 border-[#D97706] text-[#D97706] font-bold' 
                : 'opacity-65 text-gray-300 hover:opacity-100 hover:text-white'
            }`}
          >
            <FileCode size={13} />
            <span>⚙️ Edit JSON</span>
          </button>
        </nav>
        
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse shrink-0"></div>
          <span className="text-[10px] uppercase tracking-widest opacity-60 font-mono">Codex Engine Online</span>
        </div>
      </div>

      {/* Main Content Area */}
      <main className="flex-grow p-6 lg:p-12 w-full max-w-[1440px] mx-auto bg-[#F9F7F2] flex flex-col justify-between">
        
        {/* Learning Section (Opening & Variation explorer) */}
        {activeTab === 'learning' && activeExercise && (
          <LearningSection
            currentBook={currentBook}
            selectedExerciseId={selectedExerciseId}
            setSelectedExerciseId={setSelectedExerciseId}
            activeExercise={activeExercise}
            activeGame={activeGame}
            setActiveGame={setActiveGame}
            currentMoveIndex={currentMoveIndex}
            setCurrentMoveIndex={setCurrentMoveIndex}
            isExploringOpening={isExploringOpening}
            setIsExploringOpening={setIsExploringOpening}
            currentOpeningMoveIndex={currentOpeningMoveIndex}
            setCurrentOpeningMoveIndex={setCurrentOpeningMoveIndex}
            activeSideline={activeSideline}
            setActiveSideline={setActiveSideline}
            activeSidelineMoveIndex={activeSidelineMoveIndex}
            setActiveSidelineMoveIndex={setActiveSidelineMoveIndex}
            openingMoves={openingMoves}
            gameMoves={gameMoves}
            getSidelinePrefixInitialMoves={getSidelinePrefixInitialMoves}
            enableSpeech={enableSpeech}
            setEnableSpeech={setEnableSpeech}
            playbackSpeed={playbackSpeed}
            setPlaybackSpeed={setPlaybackSpeed}
            isPlaying={isPlaying}
            setIsPlaying={setIsPlaying}
          />
        )}

        {/* Games Section (Illustrative Games player) */}
        {activeTab === 'games' && activeExercise && (
          <GamesSection
            currentBook={currentBook}
            selectedExerciseId={selectedExerciseId}
            setSelectedExerciseId={setSelectedExerciseId}
            activeExercise={activeExercise}
            activeGame={activeGame}
            currentMoveIndex={currentMoveIndex}
            setCurrentMoveIndex={setCurrentMoveIndex}
            gameMoves={gameMoves}
            playbackSpeed={playbackSpeed}
            setPlaybackSpeed={setPlaybackSpeed}
            isPlaying={isPlaying}
            setIsPlaying={setIsPlaying}
          />
        )}

        {/* Exercises Section (Tactical training) */}
        {activeTab === 'exercises' && activeExercise && (
          <ExercisesSection
            currentBook={currentBook}
            selectedExerciseId={selectedExerciseId}
            setSelectedExerciseId={setSelectedExerciseId}
            activeExercise={activeExercise}
            activeGame={activeGame}
            currentMoveIndex={currentMoveIndex}
            setCurrentMoveIndex={setCurrentMoveIndex}
            gameMoves={gameMoves}
            isCorrectionMode={isCorrectionMode}
            setIsCorrectionMode={setIsCorrectionMode}
            solitairePlayer={solitairePlayer}
            setSolitairePlayer={setSolitairePlayer}
            solitaireStartFrom={solitaireStartFrom}
            setSolitaireStartFrom={setSolitaireStartFrom}
            correctionFeedback={correctionFeedback}
            setCorrectionFeedback={setCorrectionFeedback}
            resetSolitaire={resetSolitaire}
            solitaireFrontierIndex={solitaireFrontierIndex}
            solitaireSidelineFrontierIndex={solitaireSidelineFrontierIndex}
            activeSideline={activeSideline}
            activeSidelineMoveIndex={activeSidelineMoveIndex}
            openingMoves={openingMoves}
            handleCorrectMovePlay={handleCorrectMovePlay}
            handleIncorrectMovePlay={handleIncorrectMovePlay}
            handleAlternateSidelinePlayed={handleAlternateSidelinePlayed}
            getSidelinePrefixInitialMoves={getSidelinePrefixInitialMoves}
          />
        )}

        {/* Tools columns (Digitizer AI / JSON Editor) layout */}
        {(activeTab === 'digitizer' || activeTab === 'json') && (
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 w-full">
            {/* Left Column: ChessBoard & controls */}
            <div className="lg:col-span-5 flex flex-col gap-6 text-left">
              <div className="bg-[#FAF8F5] border border-black/10 rounded-2xl p-6 shadow-sm">
                <div className="mb-6">
                  <span className="text-[10px] font-sans font-bold uppercase tracking-widest text-[#D97706] block mb-1">
                    TOOLS MONITOR
                  </span>
                  <h2 className="text-2xl font-serif font-medium leading-tight text-[#1A1A1A]">
                    {activeGame.white || 'White'} vs {activeGame.black || 'Black'}
                  </h2>
                  <div className="text-[11px] font-sans uppercase tracking-wider opacity-60 mt-1">
                    {activeGame.event || 'Historical Match'}
                  </div>
                </div>

                <div className="p-4 bg-white border border-black/10 rounded-xl font-serif italic text-sm text-stone-850 leading-relaxed mb-6">
                  "{currentMoveIndex >= 0 
                    ? gameMoves[currentMoveIndex]?.commentary || "No commentary written for this position."
                    : activeGame.initial_moves 
                      ? "Precursor opening line registered. Play moves to verify transcription output."
                      : "No game moves loaded."
                  }"
                </div>

                <div className="w-full flex justify-center py-4 bg-white/40 border border-black/5 rounded-xl mb-6">
                  <ChessBoard
                    key={`tools_${selectedExerciseId}`}
                    initialMoves={activeGame.initial_moves || ""}
                    gameMoves={gameMoves}
                    currentMoveIndex={currentMoveIndex}
                    onMoveSelected={(idx) => {
                      setIsPlaying(false);
                      setCurrentMoveIndex(Math.max(-1, Math.min(gameMoves.length - 1, idx)));
                    }}
                  />
                </div>

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

            {/* Right Column: Active Tools Panel content */}
            <div className="lg:col-span-7 bg-[#141414] text-white p-6 lg:p-10 rounded-2xl border border-white/5 flex flex-col justify-between overflow-hidden">
              <div className="flex-grow overflow-y-auto min-h-[360px] pr-1">
                {activeTab === 'digitizer' && (
              <div id="ai-digitizer-panel" className="flex flex-col gap-4 text-left font-sans text-stone-300">
                
                {/* Digitizer mode toggle */}
                <div className="flex gap-2 bg-[#FAF8F5]/5 p-1 rounded border border-white/10">
                  <button
                    onClick={() => setActiveDigitizerMode('single')}
                    className={`flex-1 text-center py-2 text-[10px] uppercase font-bold tracking-wider rounded transition-all cursor-pointer ${
                      activeDigitizerMode === 'single'
                        ? 'bg-white text-stone-900 shadow'
                        : 'text-gray-400 hover:text-white hover:bg-white/5'
                    }`}
                  >
                    1. Single Page Digitizer (Add Exercise)
                  </button>
                  <button
                    onClick={() => setActiveDigitizerMode('full')}
                    className={`flex-grow text-center py-2 text-[10px] uppercase font-bold tracking-wider rounded transition-all cursor-pointer ${
                      activeDigitizerMode === 'full'
                        ? 'bg-white text-stone-900 shadow'
                        : 'text-gray-400 hover:text-white hover:bg-white/5'
                    }`}
                  >
                    2. Parse Full Book at Once
                  </button>
                </div>

                {activeDigitizerMode === 'single' ? (
                  // SINGLE PAGE DIGITIZER
                  <div className="flex flex-col gap-4">
                    <div className="space-y-0.5">
                      <h4 className="text-xs font-semibold text-white uppercase tracking-wider">Single Page Scenario Extract</h4>
                      <p className="text-[11px] text-gray-400 font-serif leading-relaxed">
                        Digitize an exercise or game from a book page. The newly extracted positions will be saved as a companion exercise inside the active book <strong>"{currentBook.title}"</strong>.
                      </p>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      {/* Left Column: Vision drop area */}
                      <div className="flex flex-col gap-1.5">
                        <label className="text-[9px] font-mono uppercase tracking-widest opacity-40">Document Visual Page Scan (.jpg, .png, .pdf)</label>
                        <div
                          onDragOver={(e) => { e.preventDefault(); setFileHoverState(true); }}
                          onDragLeave={() => setFileHoverState(false)}
                          onDrop={handleDrop}
                          onClick={() => !uploadedImageBase64 && singleFileInputRef.current?.click()}
                          className={`h-36 border rounded flex flex-col items-center justify-center p-3 gap-2 transition-all cursor-pointer relative overflow-hidden ${
                            uploadedImageBase64 
                              ? 'border-[#B91C1C]/40 bg-[#B91C1C]/5' 
                              : fileHoverState 
                                ? 'border-white bg-white/5' 
                                : 'border-white/15 bg-white/5 hover:border-white/20'
                          }`}
                        >
                          {uploadedImageBase64 ? (
                            <>
                              {uploadedImageName?.toLowerCase().endsWith('.pdf') ? (
                                <div className="absolute inset-0 bg-[#B91C1C]/10 flex items-center justify-center pointer-events-none">
                                  <FileText className="text-red-400 opacity-20" size={48} />
                                </div>
                              ) : (
                                <img 
                                  src={uploadedImageBase64} 
                                  alt="Scan Preview" 
                                  className="absolute inset-0 w-full h-full object-cover opacity-15 pointer-events-none" 
                                />
                              )}
                              <Upload className="text-[#B91C1C]" size={16} />
                              <span className="text-xs text-white max-w-full truncate px-1 font-mono hover:text-stone-300 z-10">
                                {uploadedImageName || 'Captured scan page.pdf'}
                              </span>
                              <button
                                onClick={(e) => {
                                  e.stopPropagation();
                                  setUploadedImageBase64(null);
                                  setUploadedImageName(null);
                                }}
                                className="z-10 text-[9px] text-stone-400 underline hover:text-white font-mono"
                              >
                                Remove page
                              </button>
                            </>
                          ) : (
                            <>
                              <Upload className="opacity-40" size={18} />
                              <span className="text-[11px] opacity-60 text-center">Drag book scan or PDF page here</span>
                              <span className="text-[9px] opacity-30">or click to choose file</span>
                              <input
                                  ref={singleFileInputRef}
                                  type="file"
                                  accept="image/*,application/pdf"
                                  onChange={(e) => e.target.files && handleSinglePageFile(e.target.files[0])}
                                  className="hidden"
                              />
                            </>
                          )}
                        </div>

                        {uploadedImageBase64 && uploadedImageName?.toLowerCase().endsWith('.pdf') && (
                          <div className="mt-2 p-3 bg-white/5 border border-white/10 rounded flex flex-col gap-2.5 text-stone-300">
                            <div className="flex items-center justify-between gap-2">
                              <span className="text-[10px] uppercase font-mono tracking-wider font-semibold text-red-400">PDF Single Page Scan</span>
                              <div className="flex items-center gap-1.5">
                                <span className="text-[10px] font-mono opacity-60">Page:</span>
                                <input
                                  type="number"
                                  min="1"
                                  max="999"
                                  value={pdfPageNumber}
                                  onChange={(e) => setPdfPageNumber(e.target.value)}
                                  className="w-14 bg-black/40 border border-white/15 rounded py-0.5 px-2 text-center text-xs text-white font-mono focus:outline-none focus:border-red-400/50"
                                />
                              </div>
                            </div>
                            <div className="text-[11px] text-gray-400 leading-normal border-t border-white/5 pt-2">
                              💡 <strong>Want to scan the ENTIRE book instead?</strong> You are currently in the <em>Single Page</em> mode. To scan, segment, and extract up to 10 exercises/positions from this entire PDF book at once:
                              <button
                                onClick={() => {
                                  setActiveDigitizerMode('full');
                                  setUploadedFullBookFileBase64(uploadedImageBase64);
                                  setUploadedFullBookFileName(uploadedImageName);
                                  setUploadedImageBase64(null);
                                  setUploadedImageName(null);
                                }}
                                className="mt-2 block w-full px-2.5 py-1.5 bg-[#B91C1C]/25 hover:bg-[#B91C1C]/45 text-red-200 border border-[#B91C1C]/40 rounded text-center text-[10.5px] font-mono transition-all font-semibold uppercase tracking-wider cursor-pointer"
                              >
                                Switch & Transfer to Full Book Parser
                              </button>
                            </div>
                          </div>
                        )}
                      </div>

                      {/* Right Column: Paste area */}
                      <div className="flex flex-col gap-1.5">
                        <label className="text-[9px] font-mono uppercase tracking-widest opacity-40">Page Transcription Content</label>
                        <textarea
                          value={pastedText}
                          onChange={(e) => setPastedText(e.target.value)}
                          placeholder="Paste chess move tokens here (e.g., 18 f3 b5 19 Ne3...)"
                          className="h-36 w-full bg-white/5 border border-white/10 rounded p-3 text-xs text-white font-mono resize-none focus:outline-none focus:border-white/30"
                        />
                      </div>
                    </div>

                    {/* Gemini prompt structure */}
                    <div className="flex flex-col gap-1.5 text-left">
                      <label className="text-[9px] font-mono uppercase tracking-widest opacity-40">Gemini Parsing System Instructions</label>
                      <textarea
                        value={systemPrompt}
                        onChange={(e) => setSystemPrompt(e.target.value)}
                        className="w-full bg-white/5 border border-white/10 rounded p-3 text-[10px] text-gray-300 font-mono resize-none h-14 focus:outline-none focus:border-white/20"
                      />
                    </div>

                    {/* Trigger actions */}
                    <div className="flex justify-between items-center gap-3 pt-2">
                      <div className="flex-1">
                        {parseError && (
                          <div className="text-red-400 text-[10px] font-mono max-h-12 overflow-y-auto">
                            <span>ERROR: {parseError}</span>
                          </div>
                        )}
                      </div>

                      <div className="flex gap-2">
                        {(uploadedImageBase64 || pastedText) && (
                          <button
                            onClick={() => {
                              setUploadedImageBase64(null);
                              setUploadedImageName(null);
                              setPastedText('');
                              setParseError(null);
                            }}
                            className="px-3 py-1.5 border border-white/20 text-[10px] uppercase tracking-tighter text-white hover:bg-white hover:text-black font-mono transition-all cursor-pointer"
                            title="Reset Inputs"
                          >
                            Clear
                          </button>
                        )}

                        <button
                          onClick={isParsing ? handleCancelSinglePageParsing : parseChessPage}
                          disabled={!isParsing && !uploadedImageBase64 && !pastedText}
                          className={`px-5 py-1.5 text-[10px] uppercase tracking-widest font-bold font-sans transition-all flex items-center gap-1.5 cursor-pointer ${
                            isParsing 
                              ? 'bg-red-700 text-white hover:bg-red-650' 
                              : 'bg-white text-black hover:bg-[#F9F7F2] disabled:opacity-45'
                          }`}
                        >
                          {isParsing ? (
                            <>
                              <div className="w-3 h-3 border-2 border-white/45 border-t-white rounded-full animate-spin"></div>
                              <span>Cancel Parsing</span>
                            </>
                          ) : (
                            <span>Digitize into Selected Book</span>
                          )}
                        </button>
                      </div>
                    </div>

                    {isParsing && (
                      <div className="p-4 bg-white/5 rounded border border-white/10 text-xs font-mono text-gray-400 mt-2 flex flex-col gap-2.5 text-left">
                        <div className="flex justify-between items-center bg-black/20 p-2 rounded border border-white/5">
                          <span className="text-white block font-bold uppercase text-[9px] tracking-wider">Parsing Pipeline Active</span>
                          <button
                            onClick={handleCancelSinglePageParsing}
                            className="bg-red-700 hover:bg-red-600 border border-red-500/30 text-white font-bold text-[9px] font-sans uppercase px-2 py-1 rounded cursor-pointer transition-colors"
                          >
                            Cancel Compilation
                          </button>
                        </div>
                        <p className="text-[11px] leading-relaxed">
                          Extracting printed chess coordinates... Restructuring move sequence trees... Verifying SAN standard strings. Please hold.
                        </p>
                      </div>
                    )}
                  </div>
                ) : (
                  // FULL BOOK PARSER
                  <div className="flex flex-col gap-4">
                    <div className="space-y-0.5">
                      <h4 className="text-xs font-semibold text-white uppercase tracking-wider">Extract Entire Book at Once</h4>
                      <p className="text-[11px] text-gray-400 font-serif leading-relaxed">
                        Copy and paste multiple consecutive exercises, printed game transcriptions, diagrams, or footnotes. Let Gemini AI parse, segment, and construct a brand-new multi-exercise chess book in your library automatically!
                      </p>
                    </div>

                    {/* Book Title Metadata Option */}
                    <div className="flex flex-col gap-1.5">
                      <label className="text-[9px] font-mono uppercase tracking-widest opacity-40">Dynamic Book Title (Optional)</label>
                      <input
                        type="text"
                        placeholder="e.g. Bobby Fischer Teaches Chess (Or leave empty for AI auto-detection)"
                        value={fullBookTitleInput}
                        onChange={(e) => setFullBookTitleInput(e.target.value)}
                        className="bg-white/5 border border-white/10 rounded px-3 py-2 text-xs text-white placeholder-stone-500 focus:outline-none focus:border-white/30 font-serif"
                      />
                    </div>

                    {/* Full Chess Book PDF/Image Upload Drop Zone */}
                    <div className="flex flex-col gap-1.5 font-sans">
                      <label className="text-[9px] font-mono uppercase tracking-widest opacity-40">Upload Full Chess PDF or Book Image File (.pdf, .png, .jpg)</label>
                      <div
                        onDragOver={(e) => { e.preventDefault(); setFileHoverState(true); }}
                        onDragLeave={() => setFileHoverState(false)}
                        onDrop={(e) => {
                          e.preventDefault();
                          setFileHoverState(false);
                          if (e.dataTransfer.files && e.dataTransfer.files[0]) {
                            handleFullBookFile(e.dataTransfer.files[0]);
                          }
                        }}
                        onClick={() => !uploadedFullBookFileBase64 && fullBookFileInputRef.current?.click()}
                        className={`h-32 border rounded flex flex-col items-center justify-center p-3 gap-2 transition-all cursor-pointer relative overflow-hidden ${
                          uploadedFullBookFileBase64 
                            ? 'border-[#B91C1C]/40 bg-[#B91C1C]/5' 
                            : fileHoverState 
                              ? 'border-white bg-white/5' 
                              : 'border-white/10 bg-white/5 hover:border-white/20'
                        }`}
                      >
                        {uploadedFullBookFileBase64 ? (
                          <>
                            <div className="absolute inset-0 bg-[#B91C1C]/10 flex items-center justify-center pointer-events-none">
                              <FileText className="text-red-400 opacity-20" size={56} />
                            </div>
                            <Upload className="text-[#B91C1C] animate-pulse" size={20} />
                            <span className="text-sm font-semibold text-white max-w-full truncate px-1 font-mono hover:text-stone-300 z-10">
                              {uploadedFullBookFileName || 'chess_book.pdf'}
                            </span>
                            <span className="text-[10px] text-stone-400 font-mono z-10">
                              Ready to deep segment & parse
                            </span>
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                setUploadedFullBookFileBase64(null);
                                setUploadedFullBookFileName(null);
                              }}
                              className="z-10 text-[10px] text-stone-400 underline hover:text-white font-mono mt-1"
                            >
                              Remove file
                            </button>
                          </>
                        ) : (
                          <>
                            <FileText className="opacity-30" size={24} />
                            <span className="text-[11px] opacity-70 text-center">Drag complete chess PDF book or Image here</span>
                            <span className="text-[9px] opacity-40">or click to choose file (.pdf, .png, .jpg)</span>
                            <input
                              ref={fullBookFileInputRef}
                              type="file"
                              accept="application/pdf,image/*"
                              onChange={(e) => e.target.files && handleFullBookFile(e.target.files[0])}
                              className="hidden"
                            />
                          </>
                        )}
                      </div>
                    </div>

                    {/* Page Range Inputs for PDF */}
                    {uploadedFullBookFileBase64 && uploadedFullBookFileName?.toLowerCase().endsWith('.pdf') && (
                      <div className="bg-[#B91C1C]/5 border border-[#B91C1C]/20 rounded p-3 text-stone-300 flex flex-col gap-2.5">
                        <div className="flex items-center gap-1.5 text-xs font-mono font-semibold text-red-400">
                          <Info size={14} className="text-red-450" />
                          <span>PDF Chapter / Section Scan Bounds</span>
                        </div>
                        <p className="text-[10px] text-stone-400 leading-relaxed font-serif">
                          💡 <strong>How to parse all 100+ exercises:</strong> Chess books are highly detailed, with dozens of annotations and moves. To fit the model's precise structured notation output limits, Gemini extracts up to 10 prominent exercises per scan. To scan the <strong>entire book</strong>, simply specify consecutive page ranges (for instance, pages 10 to 25) and append the parsed items directly into your active collection shelf!
                        </p>
                        <div className="flex flex-wrap items-center gap-4 mt-1">
                          <div className="flex items-center gap-2">
                            <span className="text-[10px] font-mono opacity-70">Start Page to Parse:</span>
                            <input
                              type="number"
                              min="1"
                              value={fullBookStartPage}
                              onChange={(e) => setFullBookStartPage(e.target.value)}
                              className="w-14 bg-black/40 border border-white/15 rounded px-2 py-0.5 text-xs text-white font-mono text-center focus:outline-none focus:border-red-400/50"
                            />
                          </div>
                          <div className="flex items-center gap-2">
                            <span className="text-[10px] font-mono opacity-70">End Page to Parse:</span>
                            <input
                              type="number"
                              min="1"
                              value={fullBookEndPage}
                              onChange={(e) => setFullBookEndPage(e.target.value)}
                              className="w-14 bg-black/40 border border-white/15 rounded px-2 py-0.5 text-xs text-white font-mono text-center focus:outline-none focus:border-red-400/50"
                            />
                          </div>
                        </div>

                        {lastScannedPageInfo && (
                          <div className="mt-1 p-2.5 bg-green-500/10 border border-green-500/20 rounded text-[11px] text-stone-300 leading-normal flex flex-col gap-1 font-sans">
                            <div className="flex items-center gap-1.5 font-semibold text-green-400 font-mono text-[10px] uppercase tracking-wider">
                              <span className="inline-block w-2 h-2 bg-green-500 rounded-full animate-pulse"></span>
                              <span>Scanned Chunk Completed Successfully!</span>
                            </div>
                            <div className="text-[11px] leading-relaxed">
                              We last stopped scanning at Page <strong className="text-white underline font-mono">{lastScannedPageInfo.end}</strong> (scanned chunk: <strong className="text-white font-mono">{lastScannedPageInfo.start} to {lastScannedPageInfo.end}</strong>).
                            </div>
                            <div className="opacity-75 text-[10px] border-t border-white/5 pt-1 mt-0.5 font-serif">
                              🚀 The inputs are already auto-advanced to <strong>Page {fullBookStartPage}–{fullBookEndPage}</strong>. Hit <em>"Digitize"</em> below again to process the next chunk directly into of your book!
                            </div>
                          </div>
                        )}
                      </div>
                    )}

                    {/* Import Target Strategy Dropdown */}
                    <div className="bg-white/5 border border-white/10 rounded p-3 flex flex-col gap-2.5 text-stone-300">
                      <div className="flex justify-between items-center text-xs font-semibold text-stone-200">
                        <span className="font-mono text-[9px] uppercase tracking-widest opacity-40">Import Storage Mode</span>
                      </div>
                      <div className="flex flex-wrap items-center gap-4">
                        <label className="flex items-center gap-1.5 text-xs text-stone-300 cursor-pointer">
                          <input
                            type="radio"
                            name="importTargetMode"
                            checked={importTargetMode === 'append'}
                            onChange={() => setImportTargetMode('append')}
                            className="text-red-500 focus:ring-0 focus:ring-offset-0 bg-[#333]"
                          />
                          <span>Append new exercises to an existing book portfolio</span>
                        </label>
                        <label className="flex items-center gap-1.5 text-xs text-stone-300 cursor-pointer">
                          <input
                            type="radio"
                            name="importTargetMode"
                            checked={importTargetMode === 'new'}
                            onChange={() => setImportTargetMode('new')}
                            className="text-red-500 focus:ring-0 focus:ring-offset-0 bg-[#333]"
                          />
                          <span>Create brand-new Book Portfolio</span>
                        </label>
                      </div>

                      {importTargetMode === 'append' && (
                        <div className="flex flex-col sm:flex-row items-start sm:items-center gap-2 mt-1 py-1.5 px-3 bg-black/20 rounded border border-white/5">
                          <span className="text-[9px] font-mono uppercase tracking-wider opacity-60">Target Library Destination Book:</span>
                          <select
                            value={importTargetBookId}
                            onChange={(e) => setImportTargetBookId(e.target.value)}
                            className="bg-[#222] border border-white/15 rounded text-xs text-stone-300 py-1 px-2.5 outline-none focus:outline-none focus:border-red-400/40 font-serif max-w-[260px] truncate"
                          >
                            {books.map(b => (
                              <option key={b.id} value={b.id}>
                                {b.title} ({b.exercises.length} items)
                              </option>
                            ))}
                          </select>
                        </div>
                      )}
                    </div>

                    {/* Rich text paste area */}
                    <div className="flex flex-col gap-1.5 font-sans">
                      <div className="flex justify-between items-center">
                        <label className="text-[9px] font-mono uppercase tracking-widest opacity-40">Paste Full Book Chapters & Moves Codex (Optional)</label>
                        <button
                          onClick={() => setFullBookText(`Bobby Fischer Teaches Chess

Exercise #1: Back Rank Mates
White plays to mate.
1 e4 e5 2 Nf3 d6 3 Bc4 h6 4 Nc3 Bg4 5 Nxe5 Bxd1 6 Bxf7+ Ke7 7 Nd5#

Exercise #2: Deflection Tactics
Black to play and win material.
15 Nxb5 axb5 16 Nxb5 Rxa2 17 Rxa2 Na6 18 f3 b5 19 Ne3 Bd7`)}
                          className="text-[10px] font-sans font-bold text-stone-400 hover:text-white transition-colors cursor-pointer"
                        >
                          Insert Sample Multi-Exercise Book Text
                        </button>
                      </div>
                      <textarea
                        value={fullBookText}
                        onChange={(e) => setFullBookText(e.target.value)}
                        placeholder="Paste consecutive page notations, book text segments containing several games/diagram lines..."
                        className="h-32 w-full bg-white/5 border border-white/10 rounded p-3 text-xs text-white font-mono resize-none focus:outline-none focus:border-white/30"
                      />
                    </div>

                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                      <div className="bg-white/5 rounded border border-white/10 p-3 flex flex-col gap-2">
                        <span className="text-white font-semibold text-[10px] uppercase tracking-wide">Or Create an Empty Book Portfolio</span>
                        <p className="text-[9px] text-gray-400 leading-relaxed">
                          Create an empty book space to add individual pages to manually over time.
                        </p>
                        <div className="flex gap-2 mt-auto">
                          <input
                            type="text"
                            placeholder="e.g., My Personal Endgames"
                            value={newBookTitle}
                            onChange={(e) => setNewBookTitle(e.target.value)}
                            className="flex-grow bg-black/40 border border-white/10 rounded px-2.5 py-1 text-xs text-white font-sans focus:outline-none placeholder-stone-500 min-w-0"
                          />
                          <button
                            onClick={createEmptyBook}
                            className="bg-white/10 hover:bg-white/20 border border-white/10 px-3 py-1 rounded text-[10px] font-mono text-white text-center cursor-pointer transition-all whitespace-nowrap"
                          >
                            Create
                          </button>
                        </div>
                      </div>

                      <div className="bg-white/5 rounded border border-white/10 p-3 flex flex-col gap-2">
                        <span className="text-white font-semibold text-[10px] uppercase tracking-wide">Or Restore Sample Book</span>
                        <p className="text-[9px] text-gray-400 leading-relaxed">
                          Accidentally deleted the default sample workbook? Bring it back instantly into your shelf.
                        </p>
                        <button
                          onClick={restoreDefaultSampleBook}
                          className="w-full bg-white/10 hover:bg-white/20 border border-white/10 py-1.5 rounded text-[10px] font-mono text-white text-center cursor-pointer transition-all mt-auto"
                        >
                          Restore "Modern King's Indian"
                        </button>
                      </div>
                    </div>

                    {/* Trigger full-book compile */}
                    <div className="flex justify-between items-center gap-3 pt-2">
                      <div className="flex-grow">
                        {parseFullBookError && (
                          <div className="text-red-400 text-[10px] font-mono leading-tight max-h-16 overflow-y-auto">
                            <span>ERROR: {parseFullBookError}</span>
                          </div>
                        )}
                      </div>

                      <div className="flex gap-2">
                        {(fullBookText || uploadedFullBookFileBase64) && (
                          <button
                            onClick={() => {
                              setFullBookText('');
                              setUploadedFullBookFileBase64(null);
                              setUploadedFullBookFileName(null);
                              setParseFullBookError(null);
                            }}
                            className="px-3 py-1.5 border border-white/20 text-[10px] uppercase tracking-tighter text-white hover:bg-white hover:text-black font-mono transition-colors cursor-pointer"
                          >
                            Clear
                          </button>
                        )}
                        <button
                          onClick={isParsingFullBook ? handleCancelFullBookParsing : importFullBook}
                          disabled={!isParsingFullBook && (!fullBookText.trim() && !uploadedFullBookFileBase64)}
                          className={`px-5 py-1.5 text-[10px] uppercase tracking-widest font-bold font-sans transition-colors flex items-center gap-1.5 cursor-pointer ${
                            isParsingFullBook 
                              ? 'bg-red-700 text-white hover:bg-red-650'
                              : 'bg-white text-black hover:bg-[#F9F7F2] disabled:opacity-45'
                          }`}
                        >
                          {isParsingFullBook ? (
                            <>
                              <div className="w-3 h-3 border-2 border-white/45 border-t-white rounded-full animate-spin"></div>
                              <span>Cancel Compilation</span>
                            </>
                          ) : (
                            <span>Parse & Create Book</span>
                          )}
                        </button>
                      </div>
                    </div>

                    {isParsingFullBook && (
                      <div className="p-4 bg-red-950/20 rounded border border-red-800/30 text-xs font-mono text-gray-300 leading-normal flex flex-col gap-2.5 text-left">
                        <div className="flex justify-between items-center gap-2 border-b border-white/5 pb-2">
                          <span className="text-red-400 block font-bold uppercase text-[10px] tracking-widest flex items-center gap-1.5">
                            <span className="inline-block w-2.5 h-2.5 bg-red-500 rounded-full animate-pulse"></span>
                            Multi-Page Interactive Chess Compiler Active
                          </span>
                          <div className="flex items-center gap-3">
                            <span className="text-[10px] opacity-75 font-mono px-2 py-0.5 bg-black/40 rounded border border-white/10 text-white">
                              Time: {parsingElapsedSeconds}s
                            </span>
                            <button
                              onClick={handleCancelFullBookParsing}
                              className="bg-red-700 hover:bg-red-600 text-white font-sans font-bold text-[9px] uppercase tracking-wider px-2.5 py-1 rounded border border-red-500/25 cursor-pointer transition-all"
                            >
                              Cancel
                            </button>
                          </div>
                        </div>
                        <div className="text-[11.5px] text-gray-100 flex items-start gap-2">
                          <span className="text-red-400 text-lg leading-none font-bold mt-0.5">»</span>
                          <div>
                            Current Step: <strong className="text-white">{parsingPhase}</strong>
                          </div>
                        </div>
                        <p className="text-[10px] text-stone-400 leading-relaxed font-serif pt-1">
                          💡 <strong>Speed Tip:</strong> Scanning {parseInt(fullBookStartPage,10) && parseInt(fullBookEndPage,10) ? (parseInt(fullBookEndPage,10) - parseInt(fullBookStartPage,10) + 1) : "this"} pages of highly annotated grandmaster variations usually takes around 20–45 seconds. Compiling a massive chunk (like pages 1–20 is 20 pages!) can take up to 2-3 minutes because Gemini is meticulously scanning multiple diagrams, transcribing comments, and structure-encoding every interactive move sequentially.
                        </p>
                      </div>
                    )}
                  </div>
                )}

              </div>
            )}

            {/* Tab 3: JSON Configurator */}
            {activeTab === 'json' && (
              <div id="json-editor-panel" className="flex flex-col gap-3 text-left font-mono">
                
                <div className="flex justify-between items-center">
                  <div>
                    <span className="text-[9px] font-mono uppercase tracking-widest opacity-40">System Schematics Map</span>
                  </div>

                  <button
                    onClick={handleCopyToClipboard}
                    className="px-2.5 py-1 border border-white/20 text-[9px] uppercase tracking-tighter hover:bg-white hover:text-black font-mono transition-colors"
                  >
                    {copied ? 'Successfully Copied' : 'Copy JSON Content'}
                  </button>
                </div>

                <textarea
                  value={customJsonText}
                  onChange={(e) => setCustomJsonText(e.target.value)}
                  className="w-full h-[280px] bg-black text-blue-300 font-mono text-xs p-4 border border-white/10 rounded focus:outline-none focus:border-white/30 resize-none leading-relaxed"
                />

                <div className="flex justify-end gap-2 pt-1">
                  <button
                    onClick={() => setCustomJsonText(JSON.stringify(activeGame, null, 2))}
                    className="px-3 py-1.5 border border-white/20 text-[10px] uppercase tracking-tighter text-white hover:bg-white hover:text-black font-mono transition-colors"
                  >
                    Restore
                  </button>
                  <button
                    onClick={applyJsonChanges}
                    className="px-4 py-1.5 bg-white text-black text-[10px] uppercase tracking-widest font-bold font-mono transition-colors"
                  >
                    Save Changes
                  </button>
                </div>

              </div>
            )}

          </div>

          {/* Aesthetic Editorial Metrics module matching design PDF design instructions */}
          <div className="mt-8 pt-8 border-t border-white/10 grid grid-cols-2 gap-8 font-sans">
            <div className="text-left">
              <span className="text-[9px] uppercase tracking-widest opacity-40 block mb-3 font-mono">Complexity Analysis</span>
              <div className="flex items-end gap-1 h-8">
                <div className="w-4 bg-white/20 h-[40%]"></div>
                <div className="w-4 bg-white h-[90%]"></div>
                <div className="w-4 bg-white/20 h-[30%]"></div>
                <div className="w-4 bg-white/60 h-[70%]"></div>
                <div className="w-4 bg-white/25 h-[50%]"></div>
              </div>
            </div>
            <div className="text-left">
              <span className="text-[9px] uppercase tracking-widest opacity-40 block mb-3 font-mono">Commentary Density</span>
              <div className="text-2xl font-light tracking-tight text-white font-sans">
                {gameMoves.length > 0 
                  ? ((gameMoves.filter(m => !!m.commentary).length / gameMoves.length) * 100).toFixed(1) 
                  : "0.0"
                }<span className="text-sm opacity-40 italic font-serif"> % coverage</span>
              </div>
            </div>
          </div>
            </div>
          </div>
        )}
      </main>

      {/* Aesthetic Footer */}
      <footer className="h-12 bg-black text-white flex items-center px-6 lg:px-12 justify-between text-[10px] uppercase tracking-[0.25em] font-sans">
        <span>Processing Stream: Active ({enableSpeech ? "SPEECH ON" : "SPEECH MUTED"})</span>
        <span className="opacity-40 tracking-normal hidden md:inline">Memory Usage: 422MB // Latency: 14ms // AI Engine: Gemini 3.5-Flash</span>
        <span>ID: #CX-88902</span>
      </footer>

      {/* Custom Sleek Editorial Toast Alert */}
      {alertState && (
        <div className="fixed bottom-6 right-6 z-50 max-w-sm bg-[#FAF8F5] border border-black/20 p-4 shadow-xl rounded flex items-start gap-3 transition-all duration-300 transform translate-y-0 text-left">
          <div className={`w-2 h-2 rounded-full mt-1.5 shrink-0 ${
            alertState.type === 'success' ? 'bg-emerald-600' :
            alertState.type === 'error' ? 'bg-red-600' : 'bg-amber-600'
          }`} />
          <div className="flex-grow">
            <span className="text-[9px] font-mono uppercase tracking-widest opacity-40 block mb-1">System Dispatch</span>
            <p className="text-xs font-serif italic text-stone-900 leading-relaxed">{alertState.message}</p>
          </div>
          <button 
            onClick={() => setAlertState(null)} 
            className="text-stone-400 hover:text-black font-mono text-xs p-0.5 cursor-pointer"
          >
            ×
          </button>
        </div>
      )}

      {/* Custom Architectural Confirmation Modal */}
      {confirmState && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-[2px] z-50 flex items-center justify-center p-4">
          <div className="bg-[#FAF8F5] border border-black/20 max-w-md w-full rounded p-6 shadow-2xl text-left flex flex-col gap-4">
            <div>
              <span className="text-[10px] font-mono uppercase tracking-[0.2em] text-[#B91C1C] font-bold block mb-1">Destructive Authority Confirmation</span>
              <h3 className="text-xl font-serif font-light text-stone-900 leading-snug font-serif">
                {confirmState.message}
              </h3>
            </div>
            
            <p className="text-xs text-stone-500 leading-relaxed font-serif">
              Warning: This action will purge the chosen parameters permanently from your local browser storage.
            </p>

            <div className="flex justify-end gap-3 pt-2 font-mono text-[10px]">
              <button
                onClick={() => setConfirmState(null)}
                className="px-4 py-2 border border-black/15 text-stone-600 hover:text-red-600 hover:border-red-600 transition-all rounded uppercase font-semibold tracking-wider bg-transparent cursor-pointer"
              >
                Cancel Action
              </button>
              <button
                onClick={() => {
                  confirmState.onConfirm();
                  setConfirmState(null);
                }}
                className="px-4 py-2 bg-[#B91C1C] hover:bg-red-700 text-white transition-all rounded uppercase font-bold tracking-widest shadow-md cursor-pointer"
              >
                Confirm Delete
              </button>
            </div>
          </div>
        </div>
      )}

    </div>
  );
}
