document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('.menu .has-children > a').forEach(link => {
    link.addEventListener('click', e => {
      if (window.innerWidth <= 768) {
        e.preventDefault();
        link.parentElement.classList.toggle('open');
      }
    });
  });
});

