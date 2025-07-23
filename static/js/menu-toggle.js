document.addEventListener('DOMContentLoaded', () => {
  // Move menu selector here after DOM is loaded
  const menu = document.querySelector('nav.navbar ul.menu');

  // Find every parent link of a “has-children” item
  document.querySelectorAll('nav.navbar ul.menu li.has-children > a').forEach(link => {
    link.addEventListener('click', e => {
      // Only intercept on mobile widths
      if (window.innerWidth <= 768) {
        e.preventDefault();
        const li = link.parentElement;
        // Toggle the “open” class, which CSS uses to show .submenu
        li.classList.toggle('open');
      }
    });
  });

  const burger = document.querySelector('.navbar-toggle');
  const navbar = document.querySelector('nav.navbar');

  if (burger) {
    burger.addEventListener('click', (e) => {
      e.preventDefault();
      e.stopPropagation();
      navbar.classList.toggle('expanded');
    });

    // Close menu on outside click
    document.addEventListener('click', (e) => {
      if (!navbar.contains(e.target)) {
        navbar.classList.remove('expanded');
      }
    });
  }

  // Collapse mobile menu on scroll
  let lastScrollTop = 0;

  window.addEventListener('scroll', () => {
    const st = window.pageYOffset || document.documentElement.scrollTop;
    if (st > lastScrollTop && navbar.classList.contains('expanded')) {
      navbar.classList.remove('expanded');
    }
    lastScrollTop = st <= 0 ? 0 : st;
  });
});
