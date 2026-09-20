  const [ready, setReady] = useState(false);

  useLayoutEffect(() => {
    let cancelled = false;
    const finish = () => {
      if (!cancelled) setReady(true);
    };
    const persistApi = useSelfStore.persist;
    if (!persistApi) {
      finish();
      return;
    }
    const unsub = persistApi.onFinishHydration(finish);
    void Promise.resolve(persistApi.rehydrate()).finally(finish);
    if (persistApi.hasHydrated()) finish();
    const fallback = window.setTimeout(finish, 400);
    return () => {
      cancelled = true;
      unsub();
      window.clearTimeout(fallback);
    };
  }, []);