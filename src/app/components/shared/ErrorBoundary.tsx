import React from "react";
import { AlertCircle, RefreshCw, RotateCcw } from "lucide-react";
import { usePatientStore } from "../../../api/hooks/usePatientStore";

interface ErrorBoundaryProps {
  children?: React.ReactNode;
  /** Custom label shown above the error message (e.g. "Processing Error"). */
  label?: string;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
  /** Increment to remount children on retry */
  retryKey: number;
}

/**
 * Generic error boundary that catches render errors inside any subtree.
 *
 * - Retry: remounts the child component tree (clears transient errors).
 * - Start Over: resets all patient state and navigates to the home page.
 *
 * Must be a class component — hooks cannot catch render errors.
 */
export class ErrorBoundary extends React.Component<
  ErrorBoundaryProps,
  ErrorBoundaryState
> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false, error: null, retryKey: 0 };
  }

  static getDerivedStateFromError(error: Error): Partial<ErrorBoundaryState> {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, info: React.ErrorInfo) {
    console.error("[ErrorBoundary]", error, info.componentStack);
  }

  handleRetry = () => {
    this.setState((s) => ({
      hasError: false,
      error: null,
      retryKey: s.retryKey + 1,
    }));
  };

  handleStartOver = () => {
    // Reset all patient state
    usePatientStore.getState().reset();
    // Navigate to root — avoids needing the useNavigate hook in a class component
    window.location.replace("/");
  };

  render() {
    const { hasError, error, retryKey } = this.state;
    const { children, label = "Something went wrong" } = this.props;

    if (!hasError) {
      return (
        // key forces remount on retry
        <React.Fragment key={retryKey}>{children}</React.Fragment>
      );
    }

    return (
      <div className="flex items-center justify-center min-h-screen bg-[#0A0D14] p-6">
        <div className="bg-[#13161F] border border-red-500/20 rounded-2xl p-8 max-w-md w-full text-center shadow-2xl">
          <AlertCircle className="w-12 h-12 text-red-400 mx-auto mb-4" />
          <h3 className="text-lg font-display font-bold text-white mb-1">
            {label}
          </h3>
          {error && (
            <p className="text-[#8A93B2] text-sm mb-6 font-mono break-words">
              {error.message}
            </p>
          )}

          <div className="flex gap-3 justify-center">
            <button
              onClick={this.handleRetry}
              className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-[#2A2E3B] text-white text-sm font-medium hover:bg-[#3A3F4D] transition-colors"
            >
              <RefreshCw className="w-4 h-4" />
              Retry
            </button>
            <button
              onClick={this.handleStartOver}
              className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-[#7B61FF] text-white text-sm font-medium hover:bg-[#6B51EF] transition-colors"
            >
              <RotateCcw className="w-4 h-4" />
              Start Over
            </button>
          </div>
        </div>
      </div>
    );
  }
}
