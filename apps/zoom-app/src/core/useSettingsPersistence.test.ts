import { act, renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";
import { useSettingsPersistence } from "./useSettingsPersistence";

const KEY = "snapback.test.settings";

describe("useSettingsPersistence", () => {
  beforeEach(() => {
    window.localStorage.clear();
    document.documentElement.classList.remove("dark");
    document.body.classList.remove("dark");
  });

  it("starts with sensible defaults", () => {
    const { result } = renderHook(() => useSettingsPersistence(KEY));
    expect(result.current.settings.mode).toBe("cloud");
    expect(result.current.settings.recapLength).toBe("standard");
    expect(result.current.settings.language).toBe("English");
    expect(result.current.settings.darkMode).toBe(false);
  });

  it("loads persisted settings", () => {
    window.localStorage.setItem(
      KEY,
      JSON.stringify({ mode: "local", recapLength: "detailed", language: "French", darkMode: true }),
    );
    const { result } = renderHook(() => useSettingsPersistence(KEY));
    expect(result.current.settings.mode).toBe("local");
    expect(result.current.settings.recapLength).toBe("detailed");
    expect(result.current.settings.language).toBe("French");
    expect(result.current.settings.darkMode).toBe(true);
  });

  it("update() applies a partial change and persists it", () => {
    const { result } = renderHook(() => useSettingsPersistence(KEY));
    act(() => {
      result.current.update({ language: "German", notionPageId: "page-9" });
    });
    expect(result.current.settings.language).toBe("German");
    expect(result.current.settings.notionPageId).toBe("page-9");
    const saved = JSON.parse(window.localStorage.getItem(KEY) ?? "{}");
    expect(saved.language).toBe("German");
    expect(saved.notionPageId).toBe("page-9");
  });

  it("does not persist the Notion API key", () => {
    const { result } = renderHook(() => useSettingsPersistence(KEY));
    act(() => {
      result.current.update({ notionApiKey: "secret-key" });
    });
    expect(result.current.settings.notionApiKey).toBe("secret-key");
    const saved = JSON.parse(window.localStorage.getItem(KEY) ?? "{}");
    expect(saved.notionApiKey).toBeUndefined();
  });

  it("toggleDarkMode flips the document class", () => {
    const { result } = renderHook(() => useSettingsPersistence(KEY));
    act(() => {
      result.current.toggleDarkMode();
    });
    expect(result.current.settings.darkMode).toBe(true);
    expect(document.documentElement.classList.contains("dark")).toBe(true);
  });
});
