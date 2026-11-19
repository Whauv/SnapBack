import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterEach } from "vitest";

// Without Vitest `globals`, React Testing Library's automatic cleanup is not
// registered, so unmount rendered trees between tests to avoid DOM leakage.
afterEach(() => {
  cleanup();
});
