(() => {
  const root = document.querySelector('.work-progress');
  if (!root) return;
  const buttons = [...root.querySelectorAll('[data-work-select]')];
  const feeds = [...root.querySelectorAll('[data-work-feed]')];
  const reset = root.querySelector('.work-reset');
  function select(key) {
    buttons.forEach(button => button.setAttribute('aria-pressed', String(button.dataset.workSelect === key)));
    feeds.forEach(feed => { feed.hidden = feed.dataset.workFeed !== key; });
    reset.hidden = !key;
  }
  buttons.forEach(button => button.addEventListener('click', () => {
    select(button.getAttribute('aria-pressed') === 'true' ? '' : button.dataset.workSelect);
  }));
  if (reset) reset.addEventListener('click', () => select(''));
})();
