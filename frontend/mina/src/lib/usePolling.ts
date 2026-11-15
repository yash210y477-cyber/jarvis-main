import { useEffect, useRef } from 'react';

/**
 * Run a task on a slow interval, and only while the tab is visible.
 *
 * The backend does real work for every call (SQLite reads, psutil sampling), so
 * a hidden tab must not keep knocking. Coming back to the tab refreshes at once.
 */
export function usePolling(task: () => void | Promise<void>, intervalMs: number) {
  const latest = useRef(task);
  latest.current = task;

  useEffect(() => {
    let timer: number | undefined;

    const stop = () => {
      if (timer !== undefined) window.clearInterval(timer);
      timer = undefined;
    };

    const start = () => {
      stop();
      void latest.current();
      timer = window.setInterval(() => {
        if (!document.hidden) void latest.current();
      }, intervalMs);
    };

    const onVisibility = () => {
      if (document.hidden) stop();
      else start();
    };

    if (document.hidden) stop();
    else start();

    document.addEventListener('visibilitychange', onVisibility);

    return () => {
      stop();
      document.removeEventListener('visibilitychange', onVisibility);
    };
  }, [intervalMs]);
}
