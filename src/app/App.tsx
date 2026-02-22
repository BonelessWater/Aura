import React from 'react';
import { RouterProvider } from 'react-router';
import { QueryClientProvider } from '@tanstack/react-query';
import { ReactQueryDevtools } from '@tanstack/react-query-devtools';
import { Toaster } from 'sonner';
import { queryClient } from '../api/queryClient';
import { router } from './routes';
import { useApiError } from '../api/hooks/useApiError';
import '../styles/theme.css';
import '../styles/fonts.css';

/** Inner component so hooks run inside QueryClientProvider context */
function AppInner() {
  useApiError();
  return (
    <>
      <RouterProvider router={router} />
      <Toaster
        position="top-right"
        toastOptions={{
          style: {
            background: '#13161F',
            border: '1px solid #2A2E3B',
            color: '#F0F2F8',
          },
        }}
      />
      <ReactQueryDevtools initialIsOpen={false} />
    </>
  );
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AppInner />
    </QueryClientProvider>
  );
}
