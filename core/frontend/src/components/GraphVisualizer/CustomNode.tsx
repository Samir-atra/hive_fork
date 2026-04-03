import { Handle, Position } from '@xyflow/react';
import { Bot, Sparkles, Box } from 'lucide-react';


interface CustomNodeProps {
  data: {
    label: string;
    nodeType: string;
    tools: string[];
    status?: string;
  };
}

export function CustomNode({ data }: CustomNodeProps) {
  const isStart = data.nodeType === "start" || data.label.toLowerCase() === "start";
  const isEnd = data.nodeType === "end" || data.label.toLowerCase() === "end" || data.label.toLowerCase() === "terminal";
  const isTrigger = data.nodeType === "trigger";

  const borderColor = isStart ? 'border-emerald-500' : isEnd ? 'border-red-500' : isTrigger ? 'border-amber-500' : 'border-border/60';
  const glow = data.status === "running" ? 'shadow-[0_0_10px_rgba(59,130,246,0.5)]' : '';

  return (
    <div className={`px-4 py-2 shadow-md rounded-md bg-card/90 border-2 ${borderColor} ${glow} flex flex-col gap-2 min-w-[150px]`}>
      <Handle type="target" position={Position.Top} className="w-16 !bg-primary" />

      <div className="flex items-center gap-2">
        <div className="p-1 rounded bg-muted/60 flex items-center justify-center">
          {isStart ? <Sparkles className="w-4 h-4 text-emerald-500" /> : isEnd ? <Box className="w-4 h-4 text-red-500" /> : <Bot className="w-4 h-4 text-primary" />}
        </div>
        <div className="font-semibold text-sm text-foreground">
          <span className="truncate max-w-[120px]">{data.label}</span>
        </div>
      </div>

      {data.tools && data.tools.length > 0 && (
        <div className="flex flex-wrap gap-1 mt-1">
          {data.tools.map((tool, idx) => (
            <span key={idx} className="text-[9px] px-1.5 py-0.5 rounded bg-primary/10 text-primary border border-primary/20">
              <span className="truncate max-w-[50px]">{tool}</span>
            </span>
          ))}
        </div>
      )}

      {data.status && (
        <div className="text-[10px] text-muted-foreground mt-1 capitalize">
          {data.status}
        </div>
      )}

      <Handle type="source" position={Position.Bottom} className="w-16 !bg-primary" />
    </div>
  );
}
