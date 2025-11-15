/**
 * Agent Prompt Tracker
 * Tracks interactions with AI agents (GitHub Copilot, ChatGPT, etc.)
 */

import { ActivityEvent, AgentPromptData } from '../types';

export class AgentTracker {
  private userId: string;
  private sessionId: string;

  constructor(userId: string, sessionId: string) {
    this.userId = userId;
    this.sessionId = sessionId;
  }

  /**
   * Track an agent prompt interaction
   */
  trackPrompt(
    agentName: string,
    promptLength: number,
    responseLength?: number,
    context?: string
  ): ActivityEvent {
    const event: ActivityEvent = {
      id: crypto.randomUUID(),
      sessionId: this.sessionId,
      userId: this.userId,
      type: 'agent-prompt',
      timestamp: Date.now(),
      data: {
        type: 'agent-prompt',
        agentName,
        promptLength,
        responseLength,
        context,
      },
    };

    return event;
  }

  /**
   * Track GitHub Copilot usage
   */
  trackCopilot(promptLength: number, responseLength?: number): ActivityEvent {
    return this.trackPrompt('GitHub Copilot', promptLength, responseLength, 'code-completion');
  }

  /**
   * Track custom agent usage
   */
  trackCustomAgent(
    agentName: string,
    promptLength: number,
    responseLength?: number,
    context?: string
  ): ActivityEvent {
    return this.trackPrompt(agentName, promptLength, responseLength, context);
  }

  /**
   * Get agent usage statistics for the session
   */
  async getAgentStats(events: ActivityEvent[]): Promise<{
    totalPrompts: number;
    agentBreakdown: Record<string, number>;
    avgPromptLength: number;
  }> {
    const agentEvents = events.filter((e) => e.type === 'agent-prompt');
    const agentBreakdown: Record<string, number> = {};

    let totalPromptLength = 0;

    agentEvents.forEach((event) => {
      const data = event.data as AgentPromptData;
      agentBreakdown[data.agentName] = (agentBreakdown[data.agentName] || 0) + 1;
      totalPromptLength += data.promptLength;
    });

    return {
      totalPrompts: agentEvents.length,
      agentBreakdown,
      avgPromptLength: agentEvents.length > 0 ? totalPromptLength / agentEvents.length : 0,
    };
  }
}
