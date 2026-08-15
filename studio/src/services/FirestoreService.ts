import { doc, getDoc } from "firebase/firestore";
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

export const FirestoreService = {
  async getDashboardStats(): Promise<DashboardStats> {
    const snapshot = await getDoc(doc(db, "meta", "dashboard"));

    if (!snapshot.exists()) {
      throw new Error("Firestore document meta/dashboard does not exist.");
    }

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
};
