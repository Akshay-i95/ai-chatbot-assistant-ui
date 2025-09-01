import { createContext, useContext, useState, useEffect, ReactNode } from 'react';

interface Source {
  filename: string;
  title?: string;
  department?: string;
  sub_department?: string;
  document_type?: string;
  school_types?: string[];
  download_url?: string;
  download_available?: boolean;
  file_size_mb?: number;
  relevance_score?: number;
  has_edify_metadata?: boolean;
}

interface SourcesContextType {
  sources: Source[];
  setSources: (sources: Source[]) => void;
  clearSources: () => void;
}

const SourcesContext = createContext<SourcesContextType | undefined>(undefined);

export const SourcesProvider = ({ children }: { children: ReactNode }) => {
  const [sources, setSources] = useState<Source[]>([]);

  const clearSources = () => setSources([]);

  return (
    <SourcesContext.Provider value={{ sources, setSources, clearSources }}>
      {children}
    </SourcesContext.Provider>
  );
};

export const useSources = () => {
  const context = useContext(SourcesContext);
  if (context === undefined) {
    throw new Error('useSources must be used within a SourcesProvider');
  }
  return context;
};

// Custom hook to extract sources from streamed responses
export const useSourcesFromStream = () => {
  const { setSources } = useSources();

  // Listen for sources in the global window object (temporary solution)
  useEffect(() => {
    const handleSourcesUpdate = (event: any) => {
      if (event.detail && event.detail.sources) {
        setSources(event.detail.sources);
      }
    };

    window.addEventListener('sourcesUpdate', handleSourcesUpdate);
    return () => window.removeEventListener('sourcesUpdate', handleSourcesUpdate);
  }, [setSources]);

  return { setSources };
};
