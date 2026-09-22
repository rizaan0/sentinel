import { useState } from "react";
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
      window.setTimeout(() => setCopied(false), 1500);
    } catch {
      setCopied(false);
    }
  };

  return (
    <Button variant="secondary" onClick={onCopy} className="!min-h-10 !px-3 !py-2 text-xs">
      {copied ? "Copied" : label}
    </Button>
  );
}
