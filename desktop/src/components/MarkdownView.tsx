
import React from 'react';
import { BookOpen, Link as LinkIcon, Info, AlertTriangle, CheckCircle } from 'lucide-react';
import { motion } from 'framer-motion';

interface MarkdownViewProps {
  content: string;
}

/**
 * A premium Markdown renderer for the Hive Platform.
 * 
 * Provides GitHub-flavored rendering with high-end typography, 
 * interactive elements, and semantic styling for professional documentation.
 */
const MarkdownView: React.FC<MarkdownViewProps> = ({ content }) => {
  if (!content) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-muted">
         <BookOpen size={48} className="opacity-10 mb-4" />
         <p className="text-sm">No documentation content available.</p>
      </div>
    );
  }

  const lines = content.split('\n');
  
  return (
    <div className="markdown-container">
      {lines.map((line, i) => {
        // Headers
        if (line.startsWith('# ')) {
          return (
            <motion.h1 
              key={i} 
              initial={{ opacity: 0, x: -10 }} 
              animate={{ opacity: 1, x: 0 }}
              className="text-4xl font-black gradient-text mb-8 mt-4 tracking-tight"
            >
              {line.replace('# ', '')}
            </motion.h1>
          );
        }
        if (line.startsWith('## ')) {
          return (
            <h2 key={i} className="text-2xl font-black text-white mb-6 mt-12 flex items-center gap-3 pb-3 border-b border-white/5 group">
              <span className="w-1.5 h-6 bg-primary rounded-full" />
              {line.replace('## ', '')}
              <LinkIcon size={16} className="text-muted opacity-0 group-hover:opacity-100 transition-opacity cursor-pointer ml-auto" />
            </h2>
          );
        }
        if (line.startsWith('### ')) {
          return <h3 key={i} className="text-xl font-bold text-slate-100 mb-4 mt-8">{line.replace('### ', '')}</h3>;
        }

        // Dividers
        if (line.trim() === '---') return <hr key={i} className="my-10 border-white/5" />;

        // Lists
        if (line.trim().startsWith('- ') || line.trim().startsWith('* ')) {
          const depth = line.search(/\S/);
          return (
            <div key={i} className="flex items-start gap-4 mb-3" style={{ paddingLeft: `${depth * 0.5}rem` }}>
              <div className="mt-2 w-1.5 h-1.5 rounded-full bg-primary/60 flex-shrink-0 shadow-[0_0_8px_var(--primary)]" />
              <div className="text-slate-300 text-[15px] font-medium leading-relaxed" dangerouslySetInnerHTML={{ __html: formatInline(line.trim().slice(2)) }} />
            </div>
          );
        }

        // Callouts / Blockquotes
        if (line.startsWith('> ')) {
          const text = line.replace('> ', '');
          let Icon = Info;
          let color = 'var(--info)';
          let bg = 'rgba(59, 130, 246, 0.05)';
          
          if (text.includes('**Warning**') || text.includes('⚠️')) {
            Icon = AlertTriangle;
            color = 'var(--warning)';
            bg = 'rgba(245, 158, 11, 0.05)';
          } else if (text.includes('**Check**') || text.includes('✅')) {
            Icon = CheckCircle;
            color = 'var(--success)';
            bg = 'rgba(16, 185, 129, 0.05)';
          }

          return (
            <div key={i} className="my-6 p-5 rounded-2xl border flex gap-4 transition-all hover:scale-[1.01]" style={{ backgroundColor: bg, borderColor: `${color}22` }}>
               <Icon size={20} style={{ color }} className="mt-0.5 flex-shrink-0" />
               <p className="text-sm font-medium leading-relaxed" style={{ color: 'var(--text-secondary)' }} dangerouslySetInnerHTML={{ __html: formatInline(text) }} />
            </div>
          );
        }

        // Code blocks (inline or simple multi-line)
        if (line.startsWith('`') && line.endsWith('`')) {
           return (
             <pre key={i} className="bg-black/40 p-4 rounded-xl border border-white/5 my-4 font-mono text-[13px] text-secondary">
                {line.replace(/`/g, '')}
             </pre>
           );
        }

        // Images (placeholder handling)
        if (line.includes('![') && line.includes('](')) {
           return <div key={i} className="my-8 aspect-video rounded-3xl bg-white/5 border border-white/5 flex items-center justify-center text-muted text-xs font-mono">IMAGE: {line.split('(')[1].split(')')[0]}</div>;
        }

        // Empty lines
        if (line.trim() === '') return <div key={i} className="h-4" />;

        // Standard Paragraph
        return (
          <p 
            key={i} 
            className="text-slate-400 text-[16px] leading-[1.8] mb-5 tracking-normal font-medium"
            dangerouslySetInnerHTML={{ __html: formatInline(line) }} 
          />
        );
      })}

      <style>{`
        .markdown-container {
          max-width: 900px;
          margin: 0 auto;
          padding: 2rem 4rem;
          color: var(--text-primary);
        }
        .gradient-text {
          background: linear-gradient(135deg, #fff 30%, var(--primary) 100%);
          -webkit-background-clip: text;
          -webkit-text-fill-color: transparent;
        }
        .md-link {
          color: var(--secondary);
          text-decoration: none;
          display: inline-flex;
          align-items: center;
          gap: 4px;
          font-weight: 600;
          transition: all 0.2s;
          border-bottom: 1px solid transparent;
        }
        .md-link:hover {
          color: #fff;
          border-bottom-color: var(--secondary);
        }
        .md-bold {
          color: #fff;
          font-weight: 800;
        }
        .md-italic {
           font-style: italic;
           color: var(--text-secondary);
        }
        .md-code {
          background: rgba(255,255,255,0.08);
          padding: 2px 6px;
          border-radius: 6px;
          font-family: var(--font-mono);
          font-size: 0.85em;
          color: var(--secondary);
        }
      `}</style>
    </div>
  );
};

/**
 * Formats inline Markdown elements (Bold, Italic, Links, Inline Code).
 */
function formatInline(text: string): string {
  return text
    .replace(/\*\*(.*?)\*\*/g, '<span class="md-bold">$1</span>')
    .replace(/\*(.*?)\*/g, '<span class="md-italic">$1</span>')
    .replace(/`(.*?)`/g, '<span class="md-code">$1</span>')
    .replace(/\[(.*?)\]\((.*?)\)/g, (_, label, url) => {
       return `<a href="${url}" target="_blank" class="md-link">${label} <span class="opacity-50"><svg size="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="w-3 h-3"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"></path><polyline points="15 3 21 3 21 9"></polyline><line x1="10" y1="14" x2="21" y2="3"></line></svg></span></a>`;
    });
}

export default MarkdownView;
