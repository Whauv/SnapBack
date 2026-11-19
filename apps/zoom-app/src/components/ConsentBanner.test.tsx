import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import ConsentBanner from "./ConsentBanner";

describe("ConsentBanner", () => {
  it("renders nothing when not open", () => {
    const { container } = render(
      <ConsentBanner providerLabel="AssemblyAI" open={false} accepted={false} onAccept={() => {}} onClose={() => {}} />,
    );
    expect(container).toBeEmptyDOMElement();
  });

  it("renders nothing once accepted", () => {
    const { container } = render(
      <ConsentBanner providerLabel="AssemblyAI" open accepted onAccept={() => {}} onClose={() => {}} />,
    );
    expect(container).toBeEmptyDOMElement();
  });

  it("shows the shared consent copy with the provider label", () => {
    render(<ConsentBanner providerLabel="AssemblyAI" open accepted={false} onAccept={() => {}} onClose={() => {}} />);
    expect(screen.getByText(/Audio for this lecture will be processed via AssemblyAI/)).toBeInTheDocument();
    expect(screen.getByText(/without your consent/)).toBeInTheDocument();
  });

  it("fires callbacks on the action buttons", () => {
    const onAccept = vi.fn();
    const onClose = vi.fn();
    render(<ConsentBanner providerLabel="AssemblyAI" open accepted={false} onAccept={onAccept} onClose={onClose} />);
    fireEvent.click(screen.getByText("I Understand"));
    fireEvent.click(screen.getByText("Cancel"));
    expect(onAccept).toHaveBeenCalledOnce();
    expect(onClose).toHaveBeenCalledOnce();
  });
});
