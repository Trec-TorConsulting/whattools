import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterEach, beforeAll, afterAll, beforeEach } from "vitest";
import { server } from "./mocks/server";

// Node.js 22+ has built-in localStorage that conflicts with DOM environments.
// Provide a simple Storage mock on globalThis so our code picks it up.
const store = new Map<string, string>();
const storageMock: Storage = {
  getItem: (key: string) => store.get(key) ?? null,
  setItem: (key: string, value: string) => { store.set(key, value); },
  removeItem: (key: string) => { store.delete(key); },
  clear: () => { store.clear(); },
  get length() { return store.size; },
  key: (index: number) => [...store.keys()][index] ?? null,
};
Object.defineProperty(globalThis, "localStorage", { value: storageMock, writable: true });

beforeAll(() => server.listen({ onUnhandledRequest: "warn" }));
beforeEach(() => { store.clear(); });
afterEach(() => {
  cleanup();
  server.resetHandlers();
});
afterAll(() => server.close());
