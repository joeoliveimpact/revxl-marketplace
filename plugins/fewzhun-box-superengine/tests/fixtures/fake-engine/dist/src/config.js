// Fake engine module surface the worker imports (0.12.7 dist/src), from the frozen brain-search selftest.
export const config = {
  get vaultPath() { return process.env.OBSIDIAN_VAULT_PATH; },
  apiKey: undefined, apiBaseUrl: 'https://api.openai.com/v1', apiModel: 'text-embedding-3-small', localModel: 'Xenova/multilingual-e5-small',
};
