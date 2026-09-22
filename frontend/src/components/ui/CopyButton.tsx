import { useState } from "react";
import { chromatic } from "slot-text";
import { SlotText } from "slot-text/react";
import { cue } from "../../lib/cue";
import { Button } from "./Button";

type Props = {
  value: string;
  label?: string;
};

export function CopyButton({ value, label = "Copy" }: Props) {
  const [copied, setCopied] = useState(false);

  const onCopy = async () => {
    try {
      await navigator.clipboard.writeText(value);
      setCopied(true);
      cue.copy();
      window.setTimeout(() => setCopied(false), 1500);
    } catch {
      setCopied(false);
      cue.error();
    }
  };

  return (
    <Button
      variant="secondary"
      onClick={onCopy}
      className="!min-h-10 !px-3 !py-2 text-xs"
      aria-label={copied ? "Copied" : label}
    >
      <SlotText
        text={copied ? "Copied" : label}
        options={{
          direction: copied ? "up" : "down",
          skipUnchanged: false,
          color: copied ? chromatic({ from: 190 }) : undefined,
        }}
      />
    </Button>
  );
}
