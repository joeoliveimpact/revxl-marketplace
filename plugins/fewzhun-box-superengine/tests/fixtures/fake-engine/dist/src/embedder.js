// Fake embedder.js for the worker.
export async function getContextLength() { return 512; }
export async function getEmbeddingDim() { return 384; }
export function primeEmbeddingDim() {}
