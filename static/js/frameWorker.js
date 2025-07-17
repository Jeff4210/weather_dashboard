// static/js/frameWorker.js

// A simple LRU‐ish cache of the last 20 frames
const CACHE_SIZE = 20;
const cache = new Map();

onmessage = async ({ data }) => {
  const { frameUrl } = data;

  // already in cache? send it back immediately
  if (cache.has(frameUrl)) {
    const { buffer, type } = cache.get(frameUrl);
    postMessage({ frameUrl, buffer, type }, [buffer]);
    return;
  }

  try {
    const resp = await fetch(frameUrl, { mode: 'cors' });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    const contentType = resp.headers.get('Content-Type') || 'application/octet-stream';
    const buffer = await resp.arrayBuffer();

    // cache eviction
    if (cache.size >= CACHE_SIZE) {
      const oldestKey = cache.keys().next().value;
      cache.delete(oldestKey);
    }
    cache.set(frameUrl, { buffer, type: contentType });

    // send it back as a transferable ArrayBuffer
    postMessage({ frameUrl, buffer, type: contentType }, [buffer]);
  } catch (err) {
    postMessage({ frameUrl, error: err.message });
  }
};
