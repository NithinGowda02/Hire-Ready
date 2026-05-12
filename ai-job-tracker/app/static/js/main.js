/* ============================================================
   CareerAI — main.js
   Handles: navbar scroll shadow, mobile drawer toggle,
            active nav link highlighting
   ============================================================ */

(function () {
  'use strict';

  /* ── Navbar scroll shadow ──────────────────────────────── */
  const navbar = document.getElementById('navbar');
  if (navbar) {
    const onScroll = () => {
      navbar.classList.toggle('scrolled', window.scrollY > 8);
    };
    window.addEventListener('scroll', onScroll, { passive: true });
    onScroll(); // run once on load
  }

  /* ── Mobile nav drawer toggle ──────────────────────────── */
  const toggle = document.getElementById('navToggle');
  const drawer = document.getElementById('navDrawer');

  if (toggle && drawer) {
    toggle.addEventListener('click', () => {
      const isOpen = drawer.classList.toggle('open');
      toggle.classList.toggle('open', isOpen);
      toggle.setAttribute('aria-expanded', isOpen);
      // Prevent body scroll when drawer is open
      document.body.style.overflow = isOpen ? 'hidden' : '';
    });

    // Close drawer on outside click
    document.addEventListener('click', (e) => {
      if (!navbar.contains(e.target) && !drawer.contains(e.target)) {
        closeDrawer();
      }
    });

    // Close drawer on Escape key
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') closeDrawer();
    });

    // Close when a link inside the drawer is clicked
    drawer.querySelectorAll('a').forEach(link => {
      link.addEventListener('click', closeDrawer);
    });
  }

  function closeDrawer() {
    if (!drawer) return;
    drawer.classList.remove('open');
    toggle?.classList.remove('open');
    toggle?.setAttribute('aria-expanded', 'false');
    document.body.style.overflow = '';
  }

  /* ── Active nav link ───────────────────────────────────── */
  const currentPath = window.location.pathname;
  document.querySelectorAll('.nav-link').forEach(link => {
    const href = link.getAttribute('href') || '';
    // Mark as active if the href starts with the current path segment
    if (href && href !== '/' && currentPath.startsWith(href)) {
      link.classList.add('active');
      link.setAttribute('aria-current', 'page');
    }
  });

  /* ── Smooth scroll for anchor links ───────────────────── */
  document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', (e) => {
      const target = document.querySelector(anchor.getAttribute('href'));
      if (target) {
        e.preventDefault();
        target.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }
    });
  });

})();