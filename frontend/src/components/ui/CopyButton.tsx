import { useState } from "react";
import { chromatic } from "slot-text";
import { SlotText } from "slot-text/react";
import { cue } from "../../lib/cue";
import { Button } from "./Button";
import { SfIcon } from "./icons";

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
      className="!min-h-10 gap-1.5 !px-3 !py-2 text-xs font-semibold"
      aria-label={copied ? "Copied" : label}
    >
      <span className="relative inline-flex size-3.5 items-center justify-center">
        <span
          className={`absolute inset-0 flex items-center justify-center transition-[opacity,filter,scale] duration-300 ease-[cubic-bezier(0.2,0,0,1)] ${
            copied ? "scale-100 opacity-100 blur-0" : "scale-[0.25] opacity-0 blur-[4px]"
          }`}
        >
          <SfIcon name="checkmark" weight="semibold" size={14} />
        </span>
        <span
          className={`flex items-center justify-center transition-[opacity,filter,scale] duration-300 ease-[cubic-bezier(0.2,0,0,1)] ${
            copied ? "scale-[0.25] opacity-0 blur-[4px]" : "scale-100 opacity-100 blur-0"
          }`}
        >
          <SfIcon name="doc.on.doc" weight="semibold" size={14} />
        </span>
      </span>
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
