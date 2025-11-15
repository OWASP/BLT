/**
 * Core types for the time tracking system
 */

export interface TimeTrackingSession {
  id: string;
  userId: string;
  projectId: string;
  startTime: number;
  endTime?: number;
  duration?: number;
  status: 'active' | 'paused' | 'completed';
  metadata?: Record<string, any>;
}

export interface Project {
  id: string;
  name: string;
  description?: string;
  type: 'open-source' | 'private';
  repositoryUrl?: string;
  createdAt: number;
  updatedAt: number;
}

export interface ActivityEvent {
  id: string;
  sessionId: string;
  userId: string;
  type: 'github' | 'keyboard' | 'mouse' | 'agent-prompt' | 'screenshot';
  timestamp: number;
  data: ActivityData;
  metadata?: Record<string, any>;
}

export type ActivityData = 
  | GitHubActivityData
  | KeyboardActivityData
  | MouseActivityData
  | AgentPromptData
  | ScreenshotData;

export interface GitHubActivityData {
  type: 'github';
  action: 'commit' | 'push' | 'pull-request' | 'issue' | 'review' | 'comment';
  repository: string;
  branch?: string;
  commitSha?: string;
  url?: string;
}

export interface KeyboardActivityData {
  type: 'keyboard';
  keyCount: number;
  activeTime: number; // milliseconds
  idleTime: number;
}

export interface MouseActivityData {
  type: 'mouse';
  clickCount: number;
  moveDistance: number; // pixels
  activeTime: number;
}

export interface AgentPromptData {
  type: 'agent-prompt';
  agentName: string;
  promptLength: number;
  responseLength?: number;
  context?: string;
}

export interface ScreenshotData {
  type: 'screenshot';
  localAnalysisId: string; // Reference to local analysis, never uploaded
  analysisResult?: LocalAnalysisResult;
  timestamp: number;
}

export interface LocalAnalysisResult {
  activity: 'coding' | 'debugging' | 'research' | 'communication' | 'idle' | 'unknown';
  confidence: number;
  processedLocally: true; // Always true to ensure privacy
  summary?: string; // Generic summary, no sensitive data
}

export interface User {
  id: string;
  username: string;
  email?: string;
  preferences: UserPreferences;
  createdAt: number;
}

export interface UserPreferences {
  enableScreenshots: boolean;
  screenshotInterval?: number; // minutes
  enableKeyboardTracking: boolean;
  enableMouseTracking: boolean;
  enableGitHubIntegration: boolean;
  enableAgentPromptTracking: boolean;
  privacyMode: 'full' | 'minimal';
}

export interface TrackerConfig {
  userId: string;
  projectId: string;
  preferences: UserPreferences;
  githubToken?: string; // Encrypted, never exposed
}

export interface ActivitySummary {
  sessionId: string;
  totalDuration: number;
  activeTime: number;
  idleTime: number;
  githubEvents: number;
  keyboardActivity: number;
  mouseActivity: number;
  agentPrompts: number;
  screenshots: number;
  productivity: 'high' | 'medium' | 'low';
}

export interface Env {
  TIME_TRACKING_DATA: KVNamespace;
  ACTIVITY_DATA: KVNamespace;
  TRACKER_SESSION: DurableObjectNamespace;
  [key: string]: any;
}
