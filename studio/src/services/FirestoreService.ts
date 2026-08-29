import { doc, getDoc, collection, getDocs, query, limit } from "firebase/firestore";
import { db } from "./firebase";

export interface DashboardStats {
  platforms: number;
  conversations: number;
  messages?: number;
  entities?: number;
  attachments?: number;
  knowledge_objects?: number;
  updated_at?: string;
}

export interface KnowledgeObject {
  id: string;
  title: string;
  type?: string;
  content: string;
  source_platform: string;
  source_file?: string;
  provenance?: any;
  created_at?: string;
  updated_at?: string;
  published_at?: string;
}

export interface Conversation {
  id: string;
  title: string;
  source?: string;
  source_platform?: string;
  message_count?: number;
  created?: string;
  created_date?: string;
  updated?: string;
  first_user_message?: string;
  provenance?: any;
  published_at?: string;
}

export interface Entity {
  id: string;
  value: string;
  type: string;
  conversation_id?: string;
  count?: number;
  published_at?: string;
}

export interface Attachment {
  id: string;
  file_name?: string;
  name?: string;
  summary?: string;
  processed_content?: string;
  media_type?: string;
  content_type?: string;
  conversation_id?: string;
  conversation_title?: string;
  source_platform?: string;
  platform?: string;
  published_at?: string;
}

export interface Platform {
  id: string;
  name: string;
  conversation_count?: number;
  conversations_count?: number;
  message_count?: number;
  entity_count?: number;
  attachment_count?: number;
  attachments_count?: number;
  description?: string;
  updated_at?: string;
}

export interface SearchResult {
  id: string;
  type: 'knowledge' | 'conversation' | 'entity' | 'attachment';
  title: string;
  content?: string;
  first_user_message?: string;
  source_platform?: string;
  platform?: string;
  created_at?: string;
  created_date?: string;
  message_count?: number;
  media_type?: string;
  score?: number;
}

export const FirestoreService = {
  async getDashboardStats(): Promise<DashboardStats> {
    try {
      const snapshot = await getDoc(doc(db, "meta", "dashboard"));
      if (!snapshot.exists()) return { platforms: 0, conversations: 0, knowledge_objects: 0 };
      const data = snapshot.data();
      return {
        platforms: Number(data.platforms ?? 0),
        conversations: Number(data.conversations ?? 0),
        messages: Number(data.messages ?? 0),
        entities: Number(data.entities ?? 0),
        attachments: Number(data.attachments ?? 0),
        knowledge_objects: Number(data.knowledge_objects ?? 0),
        updated_at: data.updated_at ?? undefined,
      };
    } catch (err) {
      console.error("[FIRESTORE] Error getting dashboard stats:", err);
      return { platforms: 0, conversations: 0, knowledge_objects: 0 };
    }
  },

  async getPlatforms(): Promise<Platform[]> {
    try {
      const querySnapshot = await getDocs(collection(db, "platforms"));
      return querySnapshot.docs.map(doc => ({ id: doc.id, ...doc.data() })) as Platform[];
    } catch (err) {
      console.error("[FIRESTORE] Error getting platforms:", err);
      return [];
    }
  },

  async getConversations(limitCount = 100): Promise<Conversation[]> {
    try {
      const q = query(collection(db, "conversations"), limit(limitCount));
      const querySnapshot = await getDocs(q);
      return querySnapshot.docs.map(doc => {
        const data = doc.data();
        const provenance = data.provenance || {};
        return {
          id: doc.id,
          title: data.title || doc.id,
          source: data.source,
          source_platform: data.source_platform || provenance.source_platform || 'Unmapped',
          message_count: data.message_count ?? 0,
          created: data.created,
          created_date: data.created || data.created_date,
          updated: data.updated,
          first_user_message: data.first_user_message,
          provenance: data.provenance,
          published_at: data.published_at
        };
      }) as Conversation[];
    } catch (err) {
      console.error("[FIRESTORE] Error getting conversations:", err);
      return [];
    }
  },

  async getKnowledgeObjects(limitCount = 100): Promise<KnowledgeObject[]> {
    try {
      const q = query(collection(db, "knowledgeObjects"), limit(limitCount));
      const querySnapshot = await getDocs(q);
      return querySnapshot.docs.map(doc => {
        const data = doc.data();
        return {
          id: doc.id,
          title: data.title || doc.id,
          type: data.type || 'conversation',
          content: data.content || '',
          source_platform: data.source_platform || 'Unmapped',
          source_file: data.source_file,
          provenance: data.provenance,
          created_at: data.created_at || data.published_at,
          updated_at: data.updated_at,
          published_at: data.published_at
        };
      }) as KnowledgeObject[];
    } catch (err) {
      console.error("[FIRESTORE] Error getting knowledge objects:", err);
      return [];
    }
  },

  async getEntities(limitCount = 100): Promise<Entity[]> {
    try {
      const q = query(collection(db, "entities"), limit(limitCount));
      const querySnapshot = await getDocs(q);
      return querySnapshot.docs.map(doc => ({ id: doc.id, ...doc.data() })) as Entity[];
    } catch (err) {
      console.error("[FIRESTORE] Error getting entities:", err);
      return [];
    }
  },

  async getAttachments(limitCount = 100): Promise<Attachment[]> {
    try {
      const q = query(collection(db, "attachments"), limit(limitCount));
      const querySnapshot = await getDocs(q);
      return querySnapshot.docs.map(doc => {
        const data = doc.data();
        return {
          id: doc.id,
          file_name: data.file_name || data.name || doc.id,
          name: data.name || data.file_name || doc.id,
          summary: data.summary || data.processed_content || data.ocr_text || '',
          processed_content: data.processed_content || data.summary || '',
          media_type: data.media_type || data.content_type || 'file',
          conversation_id: data.conversation_id,
          conversation_title: data.conversation_title,
          source_platform: data.source_platform || data.platform || 'General',
          platform: data.platform || data.source_platform || 'General',
          published_at: data.published_at
        };
      }) as Attachment[];
    } catch (err) {
      console.error("[FIRESTORE] Error getting attachments:", err);
      return [];
    }
  },

  /**
   * Deterministic client-side multi-collection search for Beta.
   * Matches terms across Knowledge Objects, Conversations, Entities, and Attachments.
   */
  async search(searchTerm: string): Promise<SearchResult[]> {
    if (!searchTerm || !searchTerm.trim()) return [];
    
    const term = searchTerm.trim().toLowerCase();
    const tokens = term.split(/\s+/).filter(Boolean);

    try {
      const [koSnap, convSnap, entitySnap, attSnap] = await Promise.all([
        getDocs(query(collection(db, "knowledgeObjects"), limit(100))),
        getDocs(query(collection(db, "conversations"), limit(100))),
        getDocs(query(collection(db, "entities"), limit(100))),
        getDocs(query(collection(db, "attachments"), limit(100)))
      ]);

      const results: SearchResult[] = [];

      // 1. Knowledge Objects
      koSnap.docs.forEach(doc => {
        const data = doc.data();
        const title = (data.title || doc.id).toLowerCase();
        const content = (data.content || '').toLowerCase();
        
        let score = 0;
        if (title.includes(term)) score += 10;
        if (content.includes(term)) score += 5;
        
        tokens.forEach(tok => {
          if (title.includes(tok)) score += 3;
          if (content.includes(tok)) score += 1;
        });

        if (score > 0) {
          results.push({
            id: doc.id,
            type: 'knowledge',
            title: data.title || doc.id,
            content: data.content || '',
            source_platform: data.source_platform || 'Unmapped',
            platform: data.source_platform || 'Unmapped',
            created_at: data.created_at || data.published_at,
            score
          });
        }
      });

      // 2. Conversations
      convSnap.docs.forEach(doc => {
        const data = doc.data();
        const title = (data.title || doc.id).toLowerCase();
        const firstMsg = (data.first_user_message || '').toLowerCase();
        const platform = (data.source_platform || data.provenance?.source_platform || '').toLowerCase();

        let score = 0;
        if (title.includes(term)) score += 8;
        if (firstMsg.includes(term)) score += 4;
        
        tokens.forEach(tok => {
          if (title.includes(tok)) score += 2;
          if (firstMsg.includes(tok)) score += 1;
        });

        if (score > 0) {
          results.push({
            id: doc.id,
            type: 'conversation',
            title: data.title || doc.id,
            first_user_message: data.first_user_message || '',
            source_platform: data.source_platform || data.provenance?.source_platform || 'General',
            platform: data.source_platform || data.provenance?.source_platform || 'General',
            created_date: data.created || data.created_date,
            message_count: data.message_count || 0,
            score
          });
        }
      });

      // 3. Entities
      entitySnap.docs.forEach(doc => {
        const data = doc.data();
        const val = (data.value || '').toLowerCase();
        const type = (data.type || '').toLowerCase();

        if (val.includes(term) || tokens.some(tok => val.includes(tok))) {
          results.push({
            id: doc.id,
            type: 'entity',
            title: data.value || doc.id,
            content: `Entity Type: ${data.type || 'Entity'} (Conversation: ${data.conversation_id || 'Unknown'})`,
            source_platform: 'Entity Graph',
            score: 4
          });
        }
      });

      // 4. Attachments
      attSnap.docs.forEach(doc => {
        const data = doc.data();
        const name = (data.file_name || data.name || '').toLowerCase();
        const summary = (data.summary || data.processed_content || '').toLowerCase();

        let score = 0;
        if (name.includes(term)) score += 7;
        if (summary.includes(term)) score += 3;

        if (score > 0 || tokens.some(tok => name.includes(tok) || summary.includes(tok))) {
          results.push({
            id: doc.id,
            type: 'attachment',
            title: data.file_name || data.name || doc.id,
            content: data.summary || data.processed_content || 'No summary available',
            source_platform: data.source_platform || data.platform || 'Attachment',
            media_type: data.media_type || data.content_type,
            score: score || 2
          });
        }
      });

      // Sort by score descending
      return results.sort((a, b) => (b.score || 0) - (a.score || 0));
    } catch (err) {
      console.error("[FIRESTORE] Search execution error:", err);
      return [];
    }
  }
};
