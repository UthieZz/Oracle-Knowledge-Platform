/**
 * Unified knowledge access for Studio.
 * VITE_OKP_DATA_MODE=local (default) → LocalApiStore (SQLite via okc server)
 * VITE_OKP_DATA_MODE=firestore → FirestoreService
 *
 * FirestoreService remains intact; this is a thin router only.
 */

import {
  FirestoreService,
  DashboardStats,
  KnowledgeObject,
  SearchResult,
} from "./FirestoreService";
import { LocalApiStore } from "./localApiStore";

const MODE = (
  ((import.meta as any).env?.VITE_OKP_DATA_MODE as string | undefined) || "local"
).toLowerCase();

export const isLocalDataMode = MODE !== "firestore";

export const KnowledgeStore = {
  mode(): "local" | "firestore" {
    return isLocalDataMode ? "local" : "firestore";
  },

  async getDashboardStats(): Promise<DashboardStats> {
    if (isLocalDataMode) {
      const stats = await LocalApiStore.getDashboardStats();
      return {
        platforms: stats.platforms ?? 0,
        conversations: stats.conversations ?? 0,
        knowledge_objects: stats.knowledge_objects ?? 0,
        updated_at: stats.updated_at ?? undefined,
      };
    }
    return FirestoreService.getDashboardStats();
  },

  async getKnowledgeObjects(limitCount = 100): Promise<KnowledgeObject[]> {
    if (isLocalDataMode) {
      const objects = await LocalApiStore.getKnowledgeObjects(limitCount);
      return objects.map((o) => ({
        id: o.id,
        title: o.title,
        type: o.type || "knowledge_object",
        content: o.content || "",
        source_platform: o.source_platform || "",
        created_at: o.created_at,
      }));
    }
    return FirestoreService.getKnowledgeObjects(limitCount);
  },

  async search(searchTerm: string): Promise<SearchResult[]> {
    if (isLocalDataMode) {
      const results = await LocalApiStore.search(searchTerm);
      return results.map((r) => ({
        id: r.id,
        type: (r.type as SearchResult["type"]) || "knowledge",
        title: r.title,
        content: r.snippet || r.content || "",
        source_platform: r.source_platform,
        created_at: r.created_at,
      }));
    }
    return FirestoreService.search(searchTerm);
  },
};
