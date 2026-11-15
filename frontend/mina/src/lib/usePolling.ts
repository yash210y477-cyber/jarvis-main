import { useEffect, useRef } from 'react';

/**
 * Run a task on a slow interval, and only while the tab is visible.
 *
 * The backend does real work for every call (SQLite reads, psutil sampling), so
 * a hidden tab must not keep knocking. The first load always runs, otherwise a
 * panel opened in a background tab would sit empty until it is focused; coming
 * back to the tab refreshes at once.
 */
export function usePolling(task: () => void | Promise<void>, intervalMs: number) {
  const latest = useRef(task);
  latest.current = task;

  useEffect(() => {
    // Always show something: the panel may be opened in a background tab.
    void latest.current();

    const timer = window.setInterval(() => {
      if (!document.hidden) void latest.current();
    }, intervalMs);

    const onVisibility = () => {
      if (!document.hidden) void latest.current();
    };

    document.addEventListener('visibilitychange', onVisibility);

    return () => {
      window.clearInterval(timer);
      document.removeEventListener('visibilitychange', onVisibility);
    };
  }, [intervalMs]);
}
