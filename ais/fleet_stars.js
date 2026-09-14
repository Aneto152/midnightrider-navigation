// Fleet Starred Boats - Frontend Integration
// Persistent global store with device synchronization

const FLEET_STARS_API = '/api/fleet_stars';
const STORAGE_KEY = 'fleet_stars_local';

/**
 * Synchronize local browser state with server on page load
 * Strategy: merge by union (keep anything starred on server OR client)
 */
async function initializeFleetStarSync() {
  try {
    // Read local browser state
    const localStarred = new Set(JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]'));
    
    // Fetch server state
    const serverResponse = await fetch(FLEET_STARS_API);
    if (!serverResponse.ok) {
      console.warn('[Fleet Stars] Server unavailable, using local cache');
      return;
    }
    
    const serverData = await serverResponse.json();
    const serverStarred = new Set(serverData.starred_ids || []);
    
    // Merge by union if local has content (avoid overwriting server with empty list)
    if (localStarred.size > 0) {
      // Send merge request
      const mergeResponse = await fetch(`${FLEET_STARS_API}/merge`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ starred_ids: Array.from(localStarred) })
      });
      
      if (mergeResponse.ok) {
        const merged = await mergeResponse.json();
        localStorage.setItem(STORAGE_KEY, JSON.stringify(merged.starred_ids || []));
        console.log('[Fleet Stars] Merged:', merged.starred_ids.length, 'total');
      }
    } else {
      // Local is empty, use server state
      localStorage.setItem(STORAGE_KEY, JSON.stringify(Array.from(serverStarred)));
      console.log('[Fleet Stars] Synced from server:', serverStarred.size, 'starred');
    }
  } catch (e) {
    console.warn('[Fleet Stars] Sync failed, using local cache:', e.message);
  }
}

/**
 * Get currently starred boat keys (merged server + local state)
 */
function getLocalStarred() {
  try {
    return new Set(JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]'));
  } catch {
    return new Set();
  }
}

/**
 * Toggle starred state for a single boat
 * Optimistic update: update UI immediately, persist to server
 */
async function toggleFleetStar(boatKey) {
  try {
    // Optimistic update
    const starred = getLocalStarred();
    const newState = !starred.has(boatKey);
    
    if (newState) {
      starred.add(boatKey);
    } else {
      starred.delete(boatKey);
    }
    
    localStorage.setItem(STORAGE_KEY, JSON.stringify(Array.from(starred)));
    
    // Persist to server
    const response = await fetch(`${FLEET_STARS_API}/toggle`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ boat_key: boatKey })
    });
    
    if (!response.ok) {
      console.warn('[Fleet Stars] Toggle failed, reverted locally');
      // Revert if server fails
      if (newState) {
        starred.delete(boatKey);
      } else {
        starred.add(boatKey);
      }
      localStorage.setItem(STORAGE_KEY, JSON.stringify(Array.from(starred)));
      return !newState;
    }
    
    return newState;
  } catch (e) {
    console.warn('[Fleet Stars] Toggle error:', e.message);
    return false;
  }
}

/**
 * Check if boat is starred
 */
function isFleetStarred(boatKey) {
  return getLocalStarred().has(boatKey);
}

/**
 * Refresh starred state from server (for offline → online transitions)
 */
async function refreshFleetStarState() {
  try {
    const response = await fetch(FLEET_STARS_API);
    if (response.ok) {
      const data = await response.json();
      localStorage.setItem(STORAGE_KEY, JSON.stringify(data.starred_ids || []));
      return true;
    }
  } catch (e) {
    console.warn('[Fleet Stars] Refresh failed:', e.message);
  }
  return false;
}

// Initialize on page load
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initializeFleetStarSync);
} else {
  initializeFleetStarSync();
}
