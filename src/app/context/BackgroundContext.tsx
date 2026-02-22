import React, { createContext, useContext, useState } from "react";

const BackgroundContext = createContext({
  showTitle: true,
  setShowTitle: (_: boolean) => {},
});

export const useBackgroundTitle = () => useContext(BackgroundContext);

export const BackgroundProvider = ({ children }: { children: React.ReactNode }) => {
  const [showTitle, setShowTitle] = useState(true);
  return (
    <BackgroundContext.Provider value={{ showTitle, setShowTitle }}>
      {children}
    </BackgroundContext.Provider>
  );
};
