// Simple theme toggle: toggles data-theme on <html> and stores preference in localStorage
(function(){
  const key = 'unda_theme';
  const root = document.documentElement;

  function applyTheme(t){
    if(t === 'dark') root.setAttribute('data-theme','dark');
    else root.removeAttribute('data-theme');
  }

  function getTheme(){
    const stored = localStorage.getItem(key);
    if(stored) return stored;
    // Default to prefers-color-scheme
    return window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
  }

  const theme = getTheme();
  applyTheme(theme);

  // Expose a toggle function for the UI button
  window.undaToggleTheme = function(){
    const current = root.getAttribute('data-theme') === 'dark' ? 'dark' : 'light';
    const next = current === 'dark' ? 'light' : 'dark';
    applyTheme(next);
    try{ localStorage.setItem(key, next); } catch(e){}
  };
})();
