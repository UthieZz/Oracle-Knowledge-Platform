import { doc, getDoc, collection, getDocs, query, where, orderBy, limit, addDoc, serverTimestamp, setDoc } from "firebase/firestore";
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
  type: string;
  content: string;
  source_platform: string;
  provenance?: any;
  created_at: string;
}

export interface Conversation {
  id: string;
  conversation_id: string;
  title: string;
  source_platform: string;
  message_count: number;
  created_date?: string;
  first_user_message?: string;
}

export interface Attachment {
  id: string;
  name: string;
  platform: string;
  conversation_title?: string;
  content_type?: string;
  processed_content?: string;
  ocr_text?: string;
}

export const FirestoreService = {
  async getDashboardStats(): Promise<DashboardStats> {
    const snapshot = await getDoc(doc(db, "meta", "dashboard"));
    if (!snapshot.exists()) return { platforms: 0, conversations: 0 };
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
  },

  async getPlatforms(): Promise<any[]> {
    const querySnapshot = await getDocs(collection(db, "platforms"));
    return querySnapshot.docs.map(doc => ({ id: doc.id, ...doc.data() }));
  },

  async getConversations(limitCount = 50): Promise<Conversation[]> {
    const q = query(collection(db, "conversations"), limit(limitCount));
    const querySnapshot = await getDocs(q);
    return querySnapshot.docs.map(doc => ({ id: doc.id, ...doc.data() })) as Conversation[];
  },

  async getAttachments(): Promise<Attachment[]> {
    const querySnapshot = await getDocs(collection(db, "attachments"));
    return querySnapshot.docs.map(doc => ({ id: doc.id, ...doc.data() })) as Attachment[];
  },

  async getKnowledgeObjects(): Promise<KnowledgeObject[]> {
    const querySnapshot = await getDocs(collection(db, "knowledgeObjects"));
    return querySnapshot.docs.map(doc => ({ id: doc.id, ...doc.data() })) as KnowledgeObject[];
  },

  async search(searchTerm: string): Promise<any[]> {
    if (!searchTerm) return [];
    
    // Simple client-side search across collections for now
    // In a real app with more data, we'd use Algolia or specialized Firestore indexing
    const koRef = collection(db, "knowledgeObjects");
    const convRef = collection(db, "conversations");
    
    const [koSnap, convSnap] = await Promise.all([
      getDocs(koRef),
      getDocs(convRef)
    ]);

    const results: any[] = [];
    const term = searchTerm.toLowerCase();

    koSnap.docs.forEach(doc => {
      const data = doc.data();
      if (data.title?.toLowerCase().includes(term) || data.content?.toLowerCase().includes(term)) {
        results.push({ id: doc.id, type: 'knowledge', ...data });
      }
    });

    convSnap.docs.forEach(doc => {
      const data = doc.data();
      if (data.title?.toLowerCase().includes(term) || data.first_user_message?.toLowerCase().includes(term)) {
        results.push({ id: doc.id, type: 'conversation', ...data });
      }
    });

    return results;
  },

  async publishCompiledPackage(pkg: any) {
    console.log("[FIRESTORE] Publishing compiled package:", pkg);
    
    // 1. Update stats
    await setDoc(doc(db, "meta", "dashboard"), {
      platforms: pkg.platforms_count || 0,
      conversations: pkg.conversations_count || 0,
      knowledge_objects: pkg.knowledge_objects_count || pkg.markdown_files?.length || 0,
      updated_at: new Date().toISOString()
    }, { merge: true });

    // 2. Write knowledge objects
    if (pkg.knowledge_objects) {
      for (const ko of pkg.knowledge_objects) {
        await setDoc(doc(collection(db, "knowledgeObjects"), ko.id || ko.title), {
          ...ko,
          updated_at: serverTimestamp()
        });
      }
    }

    // 3. Write conversations
    if (pkg.conversations) {
      for (const conv of pkg.conversations) {
        await setDoc(doc(collection(db, "conversations"), conv.conversation_id), {
          ...conv,
          updated_at: serverTimestamp()
        });
      }
    }
    
    return { success: true };
  }
};
