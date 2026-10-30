/* Native homepage disclosure; these enhancements do not submit or persist input. */
(() => {
  const home = document.querySelector('.home-content');
  if (!home) return;
  const details = home.querySelector('.yapic-explanation');
  const summary = details.querySelector('summary');
  const bubble = details.querySelector('.definition-bubble');
  home.classList.add('home-enhanced');

  const placeTip = () => {
    if (!details.open) return;
    const trigger = summary.getBoundingClientRect();
    const panel = bubble.getBoundingClientRect();
    const left = Math.max(20, Math.min(panel.width - 20,
      trigger.left + trigger.width / 2 - panel.left));
    bubble.style.setProperty('--tip-left', `${left}px`);
  };
  details.addEventListener('toggle', placeTip);
  new ResizeObserver(placeTip).observe(home.querySelector('.home-description'));
  document.fonts.ready.then(placeTip);
  document.addEventListener('click', event => {
    if (details.open && !details.contains(event.target)) details.open = false;
  });
  document.addEventListener('focusin', event => {
    if (details.open && !details.contains(event.target)) details.open = false;
  });
  home.addEventListener('keydown', event => {
    if (event.key === 'Escape' && details.open) {
      details.open = false;
      summary.focus();
    }
  });
})();
