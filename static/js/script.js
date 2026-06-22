/**
 * Naveen Nimmala Portfolio — script.js
 * Handles: nav, cursor, scroll animations, counters,
 *          FAQ accordion, portfolio filter, modals, back-to-top
 */

'use strict';

/* ── Helpers ─────────────────────────────────────────── */
const $ = (sel, ctx = document) => ctx.querySelector(sel);
const $$ = (sel, ctx = document) => [...ctx.querySelectorAll(sel)];

/* ═══════════════════════════════════════════════════════
   1. NAVIGATION — sticky + mobile toggle
═══════════════════════════════════════════════════════ */
(function initNav() {
  const header = $('#navHeader');
  const toggle = $('#navToggle');
  const links  = $('#navLinks');

  if (!header) return;

  const onScroll = () => {
    header.classList.toggle('scrolled', window.scrollY > 40);
  };
  window.addEventListener('scroll', onScroll, { passive: true });
  onScroll();

  if (toggle && links) {
    toggle.addEventListener('click', () => {
      const open = links.classList.toggle('open');
      toggle.classList.toggle('open', open);
      toggle.setAttribute('aria-expanded', open);
      document.body.style.overflow = open ? 'hidden' : '';
    });

    $$('a', links).forEach(a => {
      a.addEventListener('click', () => {
        links.classList.remove('open');
        toggle.classList.remove('open');
        document.body.style.overflow = '';
      });
    });
  }
})();

/* ═══════════════════════════════════════════════════════
   2. CUSTOM CURSOR
═══════════════════════════════════════════════════════ */
(function initCursor() {
  const cursor    = $('#cursor');
  const cursorDot = $('#cursorDot');
  if (!cursor || !cursorDot) return;
  if (window.matchMedia('(pointer:coarse)').matches) return;

  let mouseX = 0, mouseY = 0;
  let curX = 0, curY = 0;

  document.addEventListener('mousemove', e => {
    mouseX = e.clientX;
    mouseY = e.clientY;
    cursorDot.style.left = mouseX + 'px';
    cursorDot.style.top  = mouseY + 'px';
  });

  (function animateCursor() {
    curX += (mouseX - curX) * 0.12;
    curY += (mouseY - curY) * 0.12;
    cursor.style.left = curX + 'px';
    cursor.style.top  = curY + 'px';
    requestAnimationFrame(animateCursor);
  })();

  const hoverEls = $$('a, button, .srv-card, .port-card, .testi-card, .pricing-card, .filter-btn');
  hoverEls.forEach(el => {
    el.addEventListener('mouseenter', () => document.body.classList.add('cursor-hover'));
    el.addEventListener('mouseleave', () => document.body.classList.remove('cursor-hover'));
  });
})();

/* ═══════════════════════════════════════════════════════
   3. SCROLL REVEAL (lightweight AOS replacement)
═══════════════════════════════════════════════════════ */
(function initScrollReveal() {
  const els = $$('[data-aos]');
  if (!els.length) return;

  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        const delay = entry.target.dataset.aosDelay || 0;
        setTimeout(() => entry.target.classList.add('aos-animate'), parseInt(delay));
        observer.unobserve(entry.target);
      }
    });
  }, { threshold: 0.12, rootMargin: '0px 0px -48px 0px' });

  els.forEach(el => observer.observe(el));
})();

/* ═══════════════════════════════════════════════════════
   4. ANIMATED STAT COUNTERS
═══════════════════════════════════════════════════════ */
(function initCounters() {
  const counters = $$('.stat-num');
  if (!counters.length) return;

  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (!entry.isIntersecting) return;
      const el     = entry.target;
      const target = parseInt(el.dataset.target, 10);
      const dur    = 1600;
      const step   = 16;
      const inc    = target / (dur / step);
      let current  = 0;

      const timer = setInterval(() => {
        current += inc;
        if (current >= target) {
          el.textContent = target;
          clearInterval(timer);
        } else {
          el.textContent = Math.floor(current);
        }
      }, step);

      observer.unobserve(el);
    });
  }, { threshold: 0.5 });

  counters.forEach(el => observer.observe(el));
})();

/* ═══════════════════════════════════════════════════════
   5. SKILL BAR ANIMATION
═══════════════════════════════════════════════════════ */
(function initSkillBars() {
  const bars = $$('.sb-fill');
  if (!bars.length) return;

  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.classList.add('animated');
        observer.unobserve(entry.target);
      }
    });
  }, { threshold: 0.3 });

  bars.forEach(bar => observer.observe(bar));
})();

/* ═══════════════════════════════════════════════════════
   6. FAQ ACCORDION
═══════════════════════════════════════════════════════ */
(function initFAQ() {
  $$('.faq-q').forEach(btn => {
    btn.addEventListener('click', () => {
      const item   = btn.closest('.faq-item');
      const isOpen = item.classList.contains('open');

      $$('.faq-item.open').forEach(openItem => openItem.classList.remove('open'));

      if (!isOpen) item.classList.add('open');
    });
  });
})();

/* ═══════════════════════════════════════════════════════
   7. PORTFOLIO FILTER
═══════════════════════════════════════════════════════ */
(function initPortfolioFilter() {
  const filterBtns = $$('.filter-btn');
  const cards      = $$('.port-card');
  if (!filterBtns.length) return;

  filterBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      filterBtns.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');

      const filter = btn.dataset.filter;

      cards.forEach(card => {
        const category = card.dataset.category;
        const show     = filter === 'all' || category === filter;
        card.classList.toggle('hidden', !show);
      });
    });
  });
})();

/* ═══════════════════════════════════════════════════════
   8. PORTFOLIO MODALS
═══════════════════════════════════════════════════════ */
(function initModals() {
  $$('.port-modal-btn').forEach(btn => {
    btn.addEventListener('click', e => {
      e.preventDefault();
      const targetId = btn.getAttribute('href').replace('#', '');
      const modal    = document.getElementById(targetId);
      if (modal) {
        modal.classList.add('active');
        document.body.style.overflow = 'hidden';
      }
    });
  });

  $$('.modal-overlay').forEach(overlay => {
    overlay.addEventListener('click', e => {
      if (e.target === overlay) closeModal(overlay);
    });
    const closeBtn = $('.modal-close', overlay);
    if (closeBtn) closeBtn.addEventListener('click', () => closeModal(overlay));
  });

  document.addEventListener('keydown', e => {
    if (e.key === 'Escape') {
      $$('.modal-overlay.active').forEach(closeModal);
    }
  });

  function closeModal(modal) {
    modal.classList.remove('active');
    document.body.style.overflow = '';
  }
})();

/* ═══════════════════════════════════════════════════════
   9. BACK TO TOP
═══════════════════════════════════════════════════════ */
(function initBackToTop() {
  const btn = $('#backToTop');
  if (!btn) return;

  window.addEventListener('scroll', () => {
    btn.classList.toggle('visible', window.scrollY > 500);
  }, { passive: true });

  btn.addEventListener('click', () => {
    window.scrollTo({ top: 0, behavior: 'smooth' });
  });
})();

/* ═══════════════════════════════════════════════════════
   10. SMOOTH SCROLL for anchor links
═══════════════════════════════════════════════════════ */
(function initSmoothScroll() {
  $$('a[href^="#"]').forEach(link => {
    link.addEventListener('click', e => {
      const targetId = link.getAttribute('href');
      if (targetId === '#' || targetId.length < 2) return;
      const target = document.querySelector(targetId);
      if (target) {
        e.preventDefault();
        const navH = parseInt(getComputedStyle(document.documentElement).getPropertyValue('--nav-h')) || 72;
        const top  = target.getBoundingClientRect().top + window.scrollY - navH - 16;
        window.scrollTo({ top, behavior: 'smooth' });
      }
    });
  });
})();

/* ═══════════════════════════════════════════════════════
   11. CONTACT FORM — inline validation feedback
═══════════════════════════════════════════════════════ */
(function initFormValidation() {
  const form = $('#contactForm');
  if (!form) return;

  const requiredFields = $$('[required]', form);

  requiredFields.forEach(field => {
    field.addEventListener('blur', () => validateField(field));
    field.addEventListener('input', () => {
      if (field.classList.contains('invalid')) validateField(field);
    });
  });

  function validateField(field) {
    const valid = field.checkValidity() && field.value.trim() !== '';
    field.classList.toggle('invalid', !valid);
    field.classList.toggle('valid', valid);
  }

  const style = document.createElement('style');
  style.textContent = `
    .form-group input.valid,
    .form-group select.valid,
    .form-group textarea.valid  { border-color: var(--green) !important; }
    .form-group input.invalid,
    .form-group select.invalid,
    .form-group textarea.invalid { border-color: var(--red) !important; }
  `;
  document.head.appendChild(style);
})();

/* ═══════════════════════════════════════════════════════
   12. ACTIVE NAV LINK based on current page
═══════════════════════════════════════════════════════ */
(function highlightActiveNav() {
  const path = window.location.pathname;
  $$('.nav-links a').forEach(link => {
    const href = link.getAttribute('href');
    if (href && path.endsWith(href) && href !== '/') {
      link.classList.add('active');
    } else if (href === '/' && (path === '/' || path === '')) {
      link.classList.add('active');
    }
  });
})();

/* ═══════════════════════════════════════════════════════
   13. HERO CARD — subtle floating animation
═══════════════════════════════════════════════════════ */
(function initHeroFloat() {
  const card = $('.hero-card');
  if (!card) return;

  let t = 0;
  (function float() {
    t += 0.012;
    card.style.transform = `translateY(${Math.sin(t) * 8}px)`;
    requestAnimationFrame(float);
  })();
})();

/* ═══════════════════════════════════════════════════════
   14. PREFERS-REDUCED-MOTION: disable all animations
═══════════════════════════════════════════════════════ */
if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
  $$('[data-aos]').forEach(el => el.classList.add('aos-animate'));
}

console.log('%c✦ Naveen Nimmala Portfolio', 'color:#818CF8;font-size:14px;font-weight:bold;');
console.log('%cBuilt with Python · Flask · HTML/CSS/JS', 'color:#9CA3AF;font-size:12px;');
