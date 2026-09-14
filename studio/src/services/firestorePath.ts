import { collection, doc, CollectionReference, DocumentReference } from "firebase/firestore";
import { db } from "./firebase";

const TENANT = (import.meta as any).env?.VITE_OKP_TENANT_ID as string | undefined;
const SILO = (import.meta as any).env?.VITE_OKP_SILO_ID as string | undefined;

export function siloCollection(name: string): CollectionReference {
  if (TENANT && SILO) {
    return collection(db, "tenants", TENANT, "silos", SILO, name);
  }
  console.warn("[FIRESTORE] VITE_OKP_TENANT_ID / VITE_OKP_SILO_ID unset; falling back to root collections. Rules will deny production reads.");
  return collection(db, name);
}

export function dashboardDoc(): DocumentReference {
  if (TENANT && SILO) {
    return doc(db, "tenants", TENANT, "silos", SILO, "meta", "dashboard");
  }
  return doc(db, "meta", "dashboard");
}
