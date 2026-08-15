import { initializeApp } from "firebase/app";
import { getFirestore } from "firebase/firestore";

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

export const db = getFirestore(app);
