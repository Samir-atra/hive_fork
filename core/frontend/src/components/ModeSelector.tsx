import { Play, TestTube, Bug, Info, Sparkles } from "lucide-react";
import { cn } from "@/lib/utils";
import type { HiveMode } from "@/api/types";

interface ModeSelectorProps {
  activeMode: HiveMode;
  onModeChange: (mode: HiveMode) => void;
  disabled?: boolean;
  compact?: boolean;
}

const MODE_CONFIG: Record<HiveMode, { icon: typeof Play; label: string; color: string }> = {
  build: { icon: Sparkles, label: "Build", color: "text-purple-500" },
  run: { icon: Play, label: "Run", color: "text-green-500" },
  test: { icon: TestTube, label: "Test", color: "text-blue-500" },
  debug: { icon: Bug, label: "Debug", color: "text-orange-500" },
  info: { icon: Info, label: "Info", color: "text-cyan-500" },
};

const MODE_ORDER: HiveMode[] = ["build", "run", "test", "debug", "info"];

export default function ModeSelector({
  activeMode,
  onModeChange,
  disabled = false,
  compact = false,
}: ModeSelectorProps) {
  return (
    <div
      className={cn(
        "flex items-center gap-1 rounded-lg bg-muted/40 p-1",
        compact ? "flex-row" : "flex-col sm:flex-row"
      )}
    >
      {MODE_ORDER.map((mode) => {
        const config = MODE_CONFIG[mode];
        const Icon = config.icon;
        const isActive = activeMode === mode;

        return (
          <button
            key={mode}
            onClick={() => !disabled && onModeChange(mode)}
            disabled={disabled}
            className={cn(
              "flex items-center gap-2 rounded-md px-3 py-1.5 text-sm font-medium transition-all",
              "hover:bg-muted/60 focus:outline-none focus:ring-2 focus:ring-primary/50",
              "disabled:cursor-not-allowed disabled:opacity-50",
              isActive
                ? "bg-background shadow-sm text-foreground"
                : "text-muted-foreground hover:text-foreground",
              compact && "px-2 py-1"
            )}
            title={config.label}
          >
            <Icon
              className={cn(
                "flex-shrink-0",
                compact ? "h-4 w-4" : "h-4 w-4",
                isActive ? config.color : ""
              )}
            />
            {!compact && <span>{config.label}</span>}
          </button>
        );
      })}
    </div>
  );
}

export { MODE_CONFIG, MODE_ORDER };
export type { ModeSelectorProps };
