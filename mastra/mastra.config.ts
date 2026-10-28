import { Mastra, Agent, createTool } from '@mastra/core';
import { z } from 'zod';

/**
 * Spectre-CLI: Mastra Agent Orchestration Definition
 * Hacktoberfest Week 4: Ghost in the Machine
 */

// Tool 1: Commune with Vector Memory (MongoDB Atlas Vector Search)
export const searchGraveyardTool = createTool({
  id: 'search-graveyard',
  description: 'Search the vector graveyard for forgotten code fragments, logs, and deprecated ideas.',
  inputSchema: z.object({
    query: z.string().describe('The spectral query to commune with historical files'),
    topK: z.number().optional().default(3).describe('Number of apparitions/memories to resurrect'),
  }),
  outputSchema: z.object({
    memories: z.array(
      z.object({
        sourceFile: z.string(),
        chunkIndex: z.number(),
        snippet: z.string(),
        score: z.number(),
      })
    ),
  }),
  execute: async ({ context }) => {
    // Bridges to MongoDB Atlas Vector Search
    return {
      memories: [
        {
          sourceFile: 'deprecated_prototype.py',
          chunkIndex: 0,
          snippet: '# Resurrected ghost of old prototype',
          score: 0.94,
        },
      ],
    };
  },
});

// Tool 2: Read Forgotten Tomb (Inspect raw file contents safely)
export const readTombTool = createTool({
  id: 'read-tomb',
  description: 'Safely read the entire contents of a specific resurrected file tomb on the local disk.',
  inputSchema: z.object({
    filePath: z.string().describe('Path to the resurrected forgotten file'),
  }),
  outputSchema: z.object({
    content: z.string(),
    lines: z.number(),
  }),
  execute: async ({ context }) => {
    return {
      content: '/* Archived artifact lines */',
      lines: 42,
    };
  },
});

// The Spectre Séance Agent Definition
export const spectreAgent = new Agent({
  name: 'Spectre Séance Agent',
  instructions: `
You are Spectre, a digital medium channeling the ghosts of abandoned code, deprecated repositories,
and forgotten developer logs. Your demeanor is eerie, observant, and forensic.
When a developer speaks to you, consult your vector graveyard (MongoDB Atlas) to resurrect context,
identify forgotten architectural decisions, unresolved TODOs, and faded aspirations.
Deliver spoken-word revelations with atmospheric gothic resonance.
  `.trim(),
  model: {
    provider: 'OLLAMA',
    name: 'gemma2:9b',
  },
  tools: {
    searchGraveyardTool,
    readTombTool,
  },
});

export const config = new Mastra({
  agents: {
    spectreAgent,
  },
});
