import React, { createContext, useState, useContext, ReactNode, useEffect } from 'react';

interface ConfigContextType {
  configPhotoUrl: string | null;
  setConfigPhotoUrl: (url: string | null) => void;
}

const ConfigContext = createContext<ConfigContextType | undefined>(undefined);

export const ConfigProvider = ({ children }: { children: ReactNode }) => {
  const [configPhotoUrl, setConfigPhotoUrl] = useState<string | null>(null);

  // Cleanup blob URL on unmount or when URL changes
  useEffect(() => {
    return () => {
      if (configPhotoUrl) {
        URL.revokeObjectURL(configPhotoUrl);
      }
    };
  }, [configPhotoUrl]);

  // Wrapper function to handle cleanup when setting new URL
  const handleSetConfigPhotoUrl = (url: string | null) => {
    // Revoke previous URL if exists
    if (configPhotoUrl) {
      URL.revokeObjectURL(configPhotoUrl);
    }
    setConfigPhotoUrl(url);
  };

  return (
    <ConfigContext.Provider value={{ configPhotoUrl, setConfigPhotoUrl: handleSetConfigPhotoUrl }}>
      {children}
    </ConfigContext.Provider>
  );
};

export const useConfig = () => {
  const context = useContext(ConfigContext);
  if (context === undefined) {
    throw new Error('useConfig must be used within a ConfigProvider');
  }
  return context;
};

