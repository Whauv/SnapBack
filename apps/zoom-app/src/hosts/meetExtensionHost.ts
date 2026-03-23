import { createBrowserHostAdapter } from "./browserHost";
import type { SnapBackHostAdapter } from "./types";

export function createMeetExtensionHostAdapter(): SnapBackHostAdapter {
  const browserHost = createBrowserHostAdapter();
  return {
    ...browserHost,
    kind: "google-meet-extension",
    label: "Google Meet Extension",
    capabilities: {
      ...browserHost.capabilities,
      nativeMeetingContext: true,
      nativeAudioCapture: true,
      globalHotkey: true,
    },
    async getMeetingContext() {
      return {
        host: "google-meet-extension",
        label: "Google Meet Extension",
        surface: "meeting-side-panel",
        meetingTitle: document.title || "Google Meet",
      };
    },
    getConsentProviderLabel() {
      return "AssemblyAI tab audio capture";
    },
  };
}
