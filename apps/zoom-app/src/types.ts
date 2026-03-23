export type Mode = "cloud" | "local";
export type RecapLength = "brief" | "standard" | "detailed";

export type SessionRecord = {
  id: string;
  start_timestamp: string;
  end_timestamp?: string | null;
  full_summary?: string | null;
  mode: Mode;
  language: string;
  recap_length: RecapLength;
};

export type TranscriptChunk = {
  id: number;
  session_id: string;
  text: string;
  timestamp: string;
};

export type MissedAlert = {
  text: string;
  timestamp: string;
};

export type Recap = {
  id: number;
  from_timestamp: string;
  to_timestamp: string;
  summary: string;
  keywords: string[];
  topic_shift_detected: boolean;
  missed_alerts: MissedAlert[];
};

export type SessionTranscriptResponse = {
  session: SessionRecord;
  transcript: TranscriptChunk[];
  recaps: Recap[];
};

export type Flashcard = {
  question: string;
  answer: string;
};

export type QuizQuestion = {
  question: string;
  answer: string;
  explanation: string;
};

export type StudyPack = {
  outline: string[];
  flashcards: Flashcard[];
  quiz_questions: QuizQuestion[];
  review_priorities: string[];
};
