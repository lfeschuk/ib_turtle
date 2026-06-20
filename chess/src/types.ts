export interface ChessMove {
  move_number: number;
  player: 'W' | 'B';
  move: string; // SAN move, e.g., "b5", "Nxf2+"
  commentary: string;
}

export interface SidelineVariation {
  id: string;
  name: string;
  description: string;
  startingMoveIndex: number; // index in main game moves after which sideline diverges (-1 means divergence from the start)
  moves: ChessMove[];
}

export interface InteractiveSection {
  starting_move: number;
  moves: ChessMove[];
}

export interface ParsedChessGame {
  game_id?: string;
  white?: string;
  black?: string;
  event?: string;
  initial_moves?: string; // Moves played before the interactive section starts
  interactive_section: InteractiveSection;
  sidelines?: SidelineVariation[]; // Clickable sideline side-quests
}

export interface SampleBookPage {
  id: string;
  title: string;
  description: string;
  imageFilename: string;
  imageUrl?: string;
  textContext: string;
  preparsedJson: ParsedChessGame;
}

export interface ChessBook {
  id: string;
  title: string;
  exercises: SampleBookPage[];
}
