import React from 'react';
import { RouterProvider } from 'react-router';
import { router } from './routes';
import { BackgroundProvider } from './context/BackgroundContext';
import '../styles/theme.css';
import '../styles/fonts.css';

export default function App() {
  return (
    <BackgroundProvider>
      <RouterProvider router={router} />
    </BackgroundProvider>
  );
}
