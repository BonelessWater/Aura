import React, { createContext, useContext, useState } from 'react';

interface BackgroundContextValue {
  showTitle: boolean;
  setShowTitle: (show: boolean) => void;
}

const BackgroundContext = createContext<BackgroundContextValue>({
  showTitle: true,
  setShowTitle: () => {},
});

export const BackgroundProvider = ({ children }: { children: React.ReactNode }) => {
  const [showTitle, setShowTitle] = useState(true);

  return (
    <BackgroundContext.Provider value={{ showTitle, setShowTitle }}>
      {children}
    </BackgroundContext.Provider>
  );
};

export const useBackground = () => useContext(BackgroundContext);
export const useBackgroundTitle = () => useContext(BackgroundContext);
