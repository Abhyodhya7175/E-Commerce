// Premium product card behavior:
// - Clicking anywhere on card navigates
// - Add to Cart and Wishlist do NOT navigate
// - Uses event propagation correctly

function ucInitProductCards(root = document) {
  root.querySelectorAll('.uc-card[data-href]').forEach((card) => {
    if (card.dataset.ucBound === '1') return;
    card.dataset.ucBound = '1';

    card.addEventListener('click', (e) => {
      const href = card.dataset.href;
      if (!href) return;

      // Ignore if user clicked something "interactive"
      const interactive = e.target.closest('button, a, input, select, textarea, [role="button"]');
      if (interactive) return;

      window.location.href = href;
    });

    // Add to cart
    card.querySelectorAll('.uc-cart').forEach((btn) => {
      btn.addEventListener('click', (e) => {
        e.preventDefault();
        e.stopPropagation();
        const id = btn.dataset.cartId;
        const handler = window.ucAddToCart;
        if (typeof handler === 'function') {
          handler(id, btn);
          return;
        }

        console.log('Add to cart', id);
        btn.textContent = 'Added';
        btn.style.background = '#16a34a';
      });
    });

    // Wishlist
    card.querySelectorAll('.uc-wish').forEach((btn) => {
      btn.addEventListener('click', (e) => {
        e.preventDefault();
        e.stopPropagation();
        const id = btn.dataset.wishlistId;
        const handler = window.ucToggleWishlist;
        if (typeof handler === 'function') {
          handler(id, btn);
        }

        btn.classList.toggle('active');
        btn.querySelector('span').textContent = btn.classList.contains('active') ? '♥' : '♡';
        console.log('Wishlist toggle', id, btn.classList.contains('active'));
      });
    });
  });
}

document.addEventListener('DOMContentLoaded', () => ucInitProductCards());

