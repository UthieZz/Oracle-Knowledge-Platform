/**
 * Trusted claim-management Cloud Functions for OKP enterprise silos.
 * Deploy with Admin SDK credentials. Browser clients must not set claims.
 *
 * Callable: assignOkpClaims({ uid, access: [{tenantId, siloId, role}], admin?: boolean })
 * Caller must already hold okp_admin === true.
 */

const { onCall, HttpsError } = require("firebase-functions/v2/https");
const { initializeApp } = require("firebase-admin/app");
const { getAuth } = require("firebase-admin/auth");

initializeApp();

function normalizeAccess(access) {
  if (!Array.isArray(access) || access.length === 0) {
    throw new HttpsError("invalid-argument", "access must be a non-empty array");
  }
  return access.map((item) => {
    if (!item || !item.tenantId || !item.siloId) {
      throw new HttpsError("invalid-argument", "each access entry needs tenantId and siloId");
    }
    return {
      tenantId: String(item.tenantId),
      siloId: String(item.siloId),
      role: String(item.role || "viewer"),
    };
  });
}

exports.assignOkpClaims = onCall(async (request) => {
  if (!request.auth) {
    throw new HttpsError("unauthenticated", "Authentication required");
  }
  if (request.auth.token.okp_admin !== true) {
    throw new HttpsError("permission-denied", "okp_admin claim required");
  }

  const uid = request.data && request.data.uid;
  if (!uid || typeof uid !== "string") {
    throw new HttpsError("invalid-argument", "uid is required");
  }

  const access = normalizeAccess((request.data && request.data.access) || []);
  const silos = [...new Set(access.map((item) => `${item.tenantId}/${item.siloId}`))].sort();
  const claims = {
    okp_admin: request.data && request.data.admin === true,
    okp_silos: silos,
    okp_access: access,
  };

  await getAuth().setCustomUserClaims(uid, claims);
  return { uid, claims, message: "Claims assigned. Target user must refresh ID token." };
});
