import { initializeApp } from "firebase/app";
import {
  getFirestore,
  collection,
  getDocs,
  limit,
  query
} from "firebase/firestore";

const firebaseConfig = {
  apiKey: "AIzaSyCcf1SgpLnBWierOdqGmDZ39CygC-_NTCo",
  authDomain: "oracle-knowledge-platform.firebaseapp.com",
  projectId: "oracle-knowledge-platform",
  storageBucket: "oracle-knowledge-platform.firebasestorage.app",
  messagingSenderId: "799393957524",
  appId: "1:799393957524:web:aa48f0625eb3f279dfd681",
  measurementId: "G-14F919BCZJ"
};

const app = initializeApp(firebaseConfig);
const db = getFirestore(app);

const collections = [
  "meta",
  "platforms",
  "conversations",
  "knowledgeObjects",
  "entities",
  "attachments"
];

for (const name of collections) {
  try {
    const snap = await getDocs(query(collection(db, name), limit(3)));

    console.log(`\n=== ${name} ===`);
    console.log(`documents: ${snap.size}`);

    snap.forEach(doc => {
      console.log(`--- ${doc.id}`);
      console.log(JSON.stringify(doc.data(), null, 2));
    });
  } catch (err) {
    console.log(`\n=== ${name} ===`);
    console.log(`ERROR: ${err.message}`);
  }
}
