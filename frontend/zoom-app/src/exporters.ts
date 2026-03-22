import jsPDF from "jspdf";
import MarkdownIt from "markdown-it";
import type { Recap, SessionRecord, TranscriptChunk } from "./types";
import { formatTimestamp } from "./utils";

const markdownEngine = new MarkdownIt();

type ExportPayload = {
  session: SessionRecord | null;
  transcript: TranscriptChunk[];
  recaps: Recap[];
  fullSummary: string;
};

function buildMarkdown(payload: ExportPayload) {
  const { session, transcript, recaps, fullSummary } = payload;
  const lines = [
    "# SnapBack Notes",
    "",
    `- Lecture date: ${session?.start_timestamp ? new Date(session.start_timestamp).toLocaleDateString() : "Unknown"}`,
    `- Session ID: ${session?.id ?? "Not started"}`,
    `- Mode: ${session?.mode ?? "Unknown"}`,
    "",
    "## Full Summary",
    "",
    fullSummary || "Session summary will appear here after ending the session.",
    "",
    "## Recaps",
    "",
  ];

  if (recaps.length) {
    recaps.forEach((recap) => {
      lines.push(`### ${formatTimestamp(recap.from_timestamp)} - ${formatTimestamp(recap.to_timestamp)}`);
      lines.push("");
      lines.push(recap.summary);
      lines.push("");
      lines.push(`Keywords: ${recap.keywords.join(", ") || "None"}`);
      lines.push("");
    });
  } else {
    lines.push("No recaps generated yet.");
    lines.push("");
  }

  lines.push("## Transcript");
  lines.push("");
  if (transcript.length) {
    transcript.forEach((entry) => {
      lines.push(`- [${formatTimestamp(entry.timestamp)}] ${entry.text}`);
    });
  } else {
    lines.push("No transcript available.");
  }

  const markdown = lines.join("\n");
  markdownEngine.render(markdown);
  return markdown;
}

export function exportMarkdownNotes(payload: ExportPayload) {
  const markdown = buildMarkdown(payload);
  const blob = new Blob([markdown], { type: "text/markdown;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = "snapback-notes.md";
  anchor.click();
  URL.revokeObjectURL(url);
}

export function exportPdfNotes(payload: ExportPayload) {
  const { session, transcript, recaps, fullSummary } = payload;
  const pdf = new jsPDF();
  let cursorY = 16;

  pdf.setFontSize(18);
  pdf.text("SnapBack Notes", 12, cursorY);
  cursorY += 10;

  pdf.setFontSize(11);
  pdf.text(`Lecture date: ${session?.start_timestamp ? new Date(session.start_timestamp).toLocaleDateString() : "Unknown"}`, 12, cursorY);
  cursorY += 8;
  pdf.text(`Mode: ${session?.mode ?? "Unknown"}`, 12, cursorY);
  cursorY += 10;

  pdf.setFontSize(14);
  pdf.text("Full Summary", 12, cursorY);
  cursorY += 8;
  pdf.setFontSize(11);
  pdf.text(fullSummary || "Session summary will appear here after ending the session.", 12, cursorY, { maxWidth: 180 });
  cursorY += 24;

  pdf.setFontSize(14);
  pdf.text("Recaps", 12, cursorY);
  cursorY += 8;
  pdf.setFontSize(11);
  if (recaps.length) {
    recaps.forEach((recap) => {
      pdf.text(`${formatTimestamp(recap.from_timestamp)} - ${formatTimestamp(recap.to_timestamp)}`, 12, cursorY);
      cursorY += 6;
      pdf.text(recap.summary, 12, cursorY, { maxWidth: 180 });
      cursorY += 12;
      pdf.text(`Keywords: ${recap.keywords.join(", ") || "None"}`, 12, cursorY, { maxWidth: 180 });
      cursorY += 12;
      if (cursorY > 260) {
        pdf.addPage();
        cursorY = 18;
      }
    });
  } else {
    pdf.text("No recaps generated yet.", 12, cursorY);
    cursorY += 10;
  }

  pdf.setFontSize(14);
  pdf.text("Transcript", 12, cursorY);
  cursorY += 8;
  pdf.setFontSize(11);
  transcript.forEach((entry) => {
    pdf.text(`[${formatTimestamp(entry.timestamp)}] ${entry.text}`, 12, cursorY, { maxWidth: 180 });
    cursorY += 10;
    if (cursorY > 260) {
      pdf.addPage();
      cursorY = 18;
    }
  });

  pdf.save("snapback-notes.pdf");
}
