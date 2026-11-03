import { collection, doc, CollectionReference, DocumentReference } from "firebase/firestore";
import { db } from "./firebase";

const TENANT = (import.meta as any).env?.VITE_OKP_TENANT_ID as string | undefined;
const SILO = (import.meta as any).env?.VITE_OKP_SILO_ID as string | undefined;

function requireTenantSilo(): [string, string] {
  if (!TENANT || !SILO) {
    throw new Error(
      "[FIRESTORE] VITE_OKP_TENANT_ID and VITE_OKP_SILO_ID must be set. " +
      "Fail-closed: refusing root collection fallback to prevent unauthorised access."
    );
  }
  return [TENANT, SILO];
}

export function siloCollection(name: string): CollectionReference {
  const [tenant, silo] = requireTenantSilo();
  return collection(db, "tenants", tenant, "silos", silo, name);
}

export function dashboardDoc(): DocumentReference {
  const [tenant, silo] = requireTenantSilo();
  return doc(db, "tenants", tenant, "silos", silo, "meta", "dashboard");
}
