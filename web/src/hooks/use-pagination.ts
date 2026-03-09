import { useCallback, useState } from "react";

type PaginationState = {
  cursor: string | null;
  hasMore: boolean;
  cursors: (string | null)[];
  page: number;
};

export function usePagination() {
  const [state, setState] = useState<PaginationState>({
    cursor: null,
    hasMore: false,
    cursors: [null],
    page: 0,
  });

  const goToNext = useCallback((nextCursor: string | null) => {
    if (!nextCursor) return;
    setState((prev) => ({
      cursor: nextCursor,
      hasMore: false,
      cursors: [...prev.cursors, nextCursor],
      page: prev.page + 1,
    }));
  }, []);

  const goToPrev = useCallback(() => {
    setState((prev) => {
      if (prev.page === 0) return prev;
      const newPage = prev.page - 1;
      return {
        ...prev,
        cursor: prev.cursors[newPage] ?? null,
        page: newPage,
      };
    });
  }, []);

  const reset = useCallback(() => {
    setState({ cursor: null, hasMore: false, cursors: [null], page: 0 });
  }, []);

  const setHasMore = useCallback((hasMore: boolean) => {
    setState((prev) => ({ ...prev, hasMore }));
  }, []);

  return {
    cursor: state.cursor,
    hasMore: state.hasMore,
    page: state.page,
    canGoBack: state.page > 0,
    goToNext,
    goToPrev,
    reset,
    setHasMore,
  };
}
