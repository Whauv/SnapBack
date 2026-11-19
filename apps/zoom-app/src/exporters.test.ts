import { describe, expect, it, vi } from "vitest";
import type { Recap, SessionRecord, TranscriptChunk } from "./types";
import { buildMarkdown, exportMarkdownNotes } from "./exporters";

const session = {
  id: "sess-1",
  start_timestamp: "2026-04-07T10:00:00+00:00",
  mode: "cloud",
} as SessionRecord;

const transcript = [
  { timestamp: "2026-04-07T10:00:00+00:00", text: "Intro to gradient descent." },
] as TranscriptChunk[];

const recaps = [
  {
    from_timestamp: "2026-04-07T10:00:00+00:00",
    to_timestamp: "2026-04-07T10:05:00+00:00",
    summary: "Covered the cost function.",
    keywords: ["gradient", "descent"],
  } as Recap,
];

describe("buildMarkdown", () => {
  it("includes headings, session metadata, recaps, and transcript", () => {
    const md = buildMarkdown({ session, transcript, recaps, fullSummary: "Full recap text." });
    expect(md).toContain("# SnapBack Notes");
    expect(md).toContain("- Session ID: sess-1");
    expect(md).toContain("## Full Summary");
    expect(md).toContain("Full recap text.");
    expect(md).toContain("Covered the cost function.");
    expect(md).toContain("Keywords: gradient, descent");
    expect(md).toContain("Intro to gradient descent.");
  });

  it("shows placeholders when empty", () => {
    const md = buildMarkdown({ session: null, transcript: [], recaps: [], fullSummary: "" });
    expect(md).toContain("- Session ID: Not started");
    expect(md).toContain("No recaps generated yet.");
    expect(md).toContain("No transcript available.");
  });
});

describe("exportMarkdownNotes", () => {
  it("creates a blob download", () => {
    const createObjectURL = vi.fn(() => "blob:fake");
    const revokeObjectURL = vi.fn();
    vi.stubGlobal("URL", { ...URL, createObjectURL, revokeObjectURL });
    const click = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => {});

    exportMarkdownNotes({ session, transcript, recaps, fullSummary: "x" });

    expect(createObjectURL).toHaveBeenCalledOnce();
    expect(click).toHaveBeenCalledOnce();
    expect(revokeObjectURL).toHaveBeenCalledOnce();

    click.mockRestore();
    vi.unstubAllGlobals();
  });
});
