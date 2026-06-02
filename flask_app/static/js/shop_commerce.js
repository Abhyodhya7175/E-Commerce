(() => {
  const TOKEN = () => document.querySelector('meta[name="csrf-token"]')?.content || window.ucCsrfToken || '';

  const state = {
    cart: window.ucCartState || null,
    wishlist: window.ucWishlistState || null,
  };

  function fmt(value) {
    const number = Number(value || 0);
    return `₹${number.toLocaleString('en-IN', { maximumFractionDigits: 2 })}`;
  }

  function ensureToastWrap() {
    let wrap = document.querySelector('.uc-toast-wrap');
    if (!wrap) {
      wrap = document.createElement('div');
      wrap.className = 'uc-toast-wrap';
      document.body.appendChild(wrap);
    }
    return wrap;
  }

  function showToast(message, kind = 'success') {
    const wrap = ensureToastWrap();
    const toast = document.createElement('div');
    toast.className = `uc-toast ${kind}`;
    toast.innerHTML = `
      <div class="toast-icon">${kind === 'error' ? '!' : '✓'}</div>
      <div class="toast-body">
        <div class="toast-title">${kind === 'error' ? 'Action failed' : 'Success'}</div>
        <div class="toast-text">${message}</div>
      </div>
    `;
    wrap.appendChild(toast);
    window.setTimeout(() => {
      toast.style.opacity = '0';
      toast.style.transform = 'translateY(8px)';
      window.setTimeout(() => toast.remove(), 220);
    }, 2600);
  }

  function updateCount(selector, value) {
    document.querySelectorAll(selector).forEach((node) => {
      node.textContent = String(value);
      const shouldShow = Number(value) > 0;
      node.style.display = shouldShow ? '' : 'none';
    });
  }

  function syncBadges(cartCount, wishlistCount) {
    updateCount('[data-cart-count]', cartCount);
    updateCount('[data-wishlist-count]', wishlistCount);
  }

  function readBadgeCount(selector) {
    const node = document.querySelector(selector);
    return Number(node?.textContent || 0) || 0;
  }

  function setButtonLoading(button, loading, loadingText = 'Loading...') {
    if (!button) return;
    if (loading) {
      if (!button.dataset.originalText) {
        button.dataset.originalText = button.innerHTML;
      }
      button.disabled = true;
      button.classList.add('is-loading');
      button.innerHTML = loadingText;
      return;
    }
    button.disabled = false;
    button.classList.remove('is-loading');
    if (button.dataset.originalText) {
      button.innerHTML = button.dataset.originalText;
      delete button.dataset.originalText;
    }
  }

  function getProductId(target) {
    return target?.dataset?.wishlistId || target?.dataset?.cartId || target?.dataset?.productId || target?.closest?.('[data-product-id]')?.dataset?.productId || target?.closest?.('[data-cart-id]')?.dataset?.cartId || target?.closest?.('[data-wishlist-id]')?.dataset?.wishlistId || null;
  }

  function setWishButtonState(button, active) {
    if (!button) return;
    button.classList.toggle('active', active);
    button.setAttribute('aria-pressed', active ? 'true' : 'false');
    const textNode = button.querySelector('[data-heart]') || button;
    textNode.textContent = active ? '❤️' : '♡';
  }

  function findCartState() {
    return state.cart || window.ucCartState || { items: [], summary: { subtotal: 0, discountTotal: 0, gstTotal: 0, shippingTotal: 0, total: 0, count: 0 } };
  }

  function findWishlistState() {
    return state.wishlist || window.ucWishlistState || { items: [], count: 0 };
  }

  function applyCartState(nextState) {
    state.cart = nextState;
    window.ucCartState = nextState;
    const wishlistCount = state.wishlist?.count ?? readBadgeCount('[data-wishlist-count]');
    syncBadges(nextState.summary.count, wishlistCount);
    renderCartPage();
  }

  function applyWishlistState(nextState) {
    state.wishlist = nextState;
    window.ucWishlistState = nextState;
    const cartCount = state.cart?.summary?.count ?? readBadgeCount('[data-cart-count]');
    syncBadges(cartCount, nextState.count);
    renderWishlistPage();
  }

  async function requestJson(url, options = {}) {
    const headers = new Headers(options.headers || {});
    headers.set('Accept', 'application/json');
    if (!headers.has('Content-Type') && options.body && !(options.body instanceof FormData)) {
      headers.set('Content-Type', 'application/json');
    }
    const token = TOKEN();
    if (token) {
      headers.set('X-CSRFToken', token);
    }
    const response = await fetch(url, {
      credentials: 'same-origin',
      ...options,
      headers,
    });
    let data = {};
    try {
      data = await response.json();
    } catch (error) {
      data = {};
    }
    if (!response.ok || data.success === false) {
      throw new Error(data.error || `Request failed (${response.status})`);
    }
    return data;
  }

  function cartRowMarkup(item) {
    const imageHtml = item.imageUrl
      ? `<img src="${item.imageUrl}" alt="${item.name}">`
      : `<div class="uc-fallback" aria-hidden="true">${item.icon || '📦'}</div>`;

    const hasDiscount = Number(item.mrp || 0) > Number(item.discountPrice || 0);
    const stockLabel = String(item.stockStatus || 'In Stock').toLowerCase();
    const stockClass = stockLabel.includes('out') ? 'out' : stockLabel.includes('low') ? 'low' : '';

    return `
      <article class="uc-cart-line" data-cart-line="${item.id}">
        <div class="uc-cart-media">${imageHtml}</div>
        <div class="uc-cart-content">
          <div>
            <h3 class="uc-product-title">${item.name}</h3>
            <div class="uc-product-meta">
              ${item.brand ? `<span>${item.brand}</span>` : ''}
              ${item.category ? `<span>${item.category}</span>` : ''}
              ${item.stockStatus ? `<span class="uc-stock ${stockClass}">${item.stockStatus}</span>` : ''}
            </div>
          </div>
          <div class="uc-price-row">
            <div class="uc-price-now">${fmt(item.discountPrice)}</div>
            ${hasDiscount ? `<div class="uc-price-was">${fmt(item.mrp)}</div>` : ''}
            <div class="uc-pill">Discount ${Number(item.discountPercent || 0)}%</div>
          </div>
          <div class="uc-product-meta">
            <span>GST ${Number(item.gstPercentage || 0)}% ${item.gstType || ''}</span>
            ${item.freeShipping ? '<span>Free shipping</span>' : `<span>Shipping ${fmt(item.shippingCharges || 0)}</span>`}
          </div>
          <div class="uc-line-actions">
            <div class="uc-qty" data-cart-qty-group="${item.id}">
              <button type="button" class="uc-qty-btn" data-cart-action="decrease" data-cart-step="-1" data-cart-id="${item.id}" aria-label="Decrease quantity">−</button>
              <input type="number" min="1" max="${item.stockQuantity || 999}" value="${item.quantity}" data-cart-qty-input="${item.id}">
              <button type="button" class="uc-qty-btn" data-cart-action="increase" data-cart-step="1" data-cart-id="${item.id}" aria-label="Increase quantity">+</button>
            </div>
            <button type="button" class="uc-action-link subtle" data-cart-remove="${item.id}">Remove</button>
            <button type="button" class="uc-action-link ghost" data-save-later="${item.id}">Save for later</button>
          </div>
        </div>
      </article>
    `;
  }

  function renderCartPage() {
    const root = document.getElementById('uc-cart-list');
    if (!root) return;
    const cart = findCartState();
    const items = cart.items || [];
    const hasServerRenderedItems = root.querySelectorAll('.uc-cart-line').length > 0;

    if (!items.length && hasServerRenderedItems) {
      return;
    }

    if (!items.length) {
      root.innerHTML = `
        <div class="uc-empty-state">
          <div class="uc-empty-illustration">🛒</div>
          <h2>Your cart is empty</h2>
          <p>Discover premium products and build your cart with one tap. Items you add will appear here instantly.</p>
          <a class="uc-btn uc-btn-primary" href="/shop/">Continue shopping</a>
        </div>
      `;
    } else {
      root.innerHTML = items.map(cartRowMarkup).join('');
    }

    const summary = cart.summary || {};
    document.querySelectorAll('[data-summary-value="subtotal"]').forEach((node) => (node.textContent = fmt(summary.subtotal)));
    document.querySelectorAll('[data-summary-value="discount"]').forEach((node) => (node.textContent = `-${fmt(summary.discountTotal)}`));
    document.querySelectorAll('[data-summary-value="gst"]').forEach((node) => (node.textContent = fmt(summary.gstTotal)));
    document.querySelectorAll('[data-summary-value="shipping"]').forEach((node) => (node.textContent = fmt(summary.shippingTotal)));
    document.querySelectorAll('[data-summary-value="total"]').forEach((node) => (node.textContent = fmt(summary.total)));
    document.querySelectorAll('[data-cart-line-count]').forEach((node) => (node.textContent = String(summary.count || 0)));

    const progressTrack = document.querySelector('.uc-progress-track[data-progress]');
    if (progressTrack) {
      const progress = Number(progressTrack.dataset.progress || 0);
      const fill = progressTrack.querySelector('.uc-progress-fill');
      if (fill) fill.style.width = `${Math.max(0, Math.min(100, progress))}%`;
    }
  }

  function wishlistCardMarkup(item) {
    const imageHtml = item.imageUrl
      ? `<img src="${item.imageUrl}" alt="${item.name}">`
      : `<div class="uc-fallback" aria-hidden="true">${item.icon || '📦'}</div>`;
    const stockLabel = String(item.stockStatus || 'In Stock').toLowerCase();
    const stockClass = stockLabel.includes('out') ? 'out' : stockLabel.includes('low') ? 'low' : '';
    const hasDiscount = Number(item.mrp || 0) > Number(item.discountPrice || 0);
    const rating = Number(item.rating || 0).toFixed(1);

    return `
      <article class="uc-wishlist-card" data-wishlist-card="${item.id}">
        <div class="uc-wishlist-media">${imageHtml}</div>
        <div class="uc-wishlist-body">
          <div>
            <h3 class="uc-product-title">${item.name}</h3>
            <div class="uc-product-meta">
              ${item.brand ? `<span>${item.brand}</span>` : ''}
              ${item.category ? `<span>${item.category}</span>` : ''}
            </div>
          </div>
          <div class="uc-price-row">
            <div class="uc-price-now">${fmt(item.discountPrice)}</div>
            ${hasDiscount ? `<div class="uc-price-was">${fmt(item.mrp)}</div>` : ''}
          </div>
          <div class="uc-wishlist-rating">★ ${rating} <span class="uc-product-meta">(${Number(item.reviewCount || 0)} reviews)</span></div>
          <div class="uc-product-meta">
            <span class="uc-stock ${stockClass}">${item.stockStatus || 'In Stock'}</span>
          </div>
          <div class="uc-card-actions">
            <button type="button" class="uc-btn uc-btn-primary" data-move-to-cart="${item.id}">Move to cart</button>
            <button type="button" class="uc-btn uc-btn-soft" data-wishlist-remove="${item.id}">Remove</button>
          </div>
        </div>
      </article>
    `;
  }

  function renderWishlistPage() {
    const root = document.getElementById('uc-wishlist-grid');
    if (!root) return;
    const wishlist = findWishlistState();
    const items = wishlist.items || [];
    if (!items.length) {
      root.innerHTML = `
        <div class="uc-empty-state" style="grid-column: 1 / -1;">
          <div class="uc-empty-illustration">♡</div>
          <h2>Your wishlist is empty</h2>
          <p>Tap the heart on any product to save it for later. Wishlisted items stay synced across refreshes and logins.</p>
          <a class="uc-btn uc-btn-primary" href="/shop/">Explore products</a>
        </div>
      `;
    } else {
      root.innerHTML = items.map(wishlistCardMarkup).join('');
    }

    document.querySelectorAll('[data-wishlist-count-display]').forEach((node) => (node.textContent = String(wishlist.count || 0)));
  }

  async function toggleWishlist(productId, button) {
    if (!productId) return;
    if (button) {
      button.disabled = true;
      button.classList.add('is-loading');
    }
    try {
      const data = await requestJson(`/wishlist/add/${productId}`, { method: 'POST', body: JSON.stringify({}) });
      const nextState = {
        items: data.wishlist || [],
        count: Number(data.wishlist_count || 0),
      };
      applyWishlistState(nextState);
      const active = Boolean(data.active);
      setWishButtonState(button, active);
      showToast(data.message || (active ? 'Added to Wishlist' : 'Removed from Wishlist'));
    } catch (error) {
      showToast(error.message, 'error');
    } finally {
      if (button) {
        button.disabled = false;
        button.classList.remove('is-loading');
      }
    }
  }

  async function addToCart(productId, button, quantity = 1) {
    if (!productId) return;
    const productStock = Number(button?.dataset?.stock || button?.dataset?.productStock || 0);
    if (productStock > 0 && Number(quantity) > productStock) {
      showToast('Requested quantity exceeds available stock.', 'error');
      return;
    }
    setButtonLoading(button, true, 'Adding...');
    try {
      const data = await requestJson(`/cart/add/${productId}`, {
        method: 'POST',
        body: JSON.stringify({ quantity }),
      });
      const nextState = {
        items: data.cart || [],
        summary: data.summary || findCartState().summary,
      };
      applyCartState(nextState);
      showToast(data.message || 'Added to Cart');
    } catch (error) {
      showToast(error.message, 'error');
    } finally {
      setButtonLoading(button, false);
    }
  }

  async function updateCart(productId, quantity, button) {
    if (!productId) return;
    try {
      const data = await requestJson(`/cart/update/${productId}`, {
        method: 'POST',
        body: JSON.stringify({ quantity }),
      });
      applyCartState({ items: data.cart || [], summary: data.summary || findCartState().summary });
      showToast(data.message || 'Cart updated');
    } catch (error) {
      showToast(error.message, 'error');
    } finally {
      if (button) {
        button.classList.remove('is-loading');
      }
    }
  }

  async function removeFromCart(productId, button) {
    if (!productId) return;
    setButtonLoading(button, true, 'Removing...');
    try {
      const data = await requestJson(`/cart/remove/${productId}`, { method: 'POST', body: JSON.stringify({}) });
      applyCartState({ items: data.cart || [], summary: data.summary || findCartState().summary });
      showToast(data.message || 'Removed from Cart');
    } catch (error) {
      showToast(error.message, 'error');
    } finally {
      setButtonLoading(button, false);
    }
  }

  async function removeFromWishlist(productId, button) {
    if (!productId) return;
    setButtonLoading(button, true, 'Removing...');
    try {
      const data = await requestJson(`/wishlist/remove/${productId}`, { method: 'POST', body: JSON.stringify({}) });
      const nextState = {
        items: data.wishlist || [],
        count: Number(data.wishlist_count || 0),
      };
      applyWishlistState(nextState);
      showToast(data.message || 'Removed from Wishlist');
    } catch (error) {
      showToast(error.message, 'error');
    } finally {
      setButtonLoading(button, false);
    }
  }

  async function moveWishlistToCart(productId, button) {
    if (!productId) return;
    setButtonLoading(button, true, 'Moving...');
    try {
      const data = await requestJson(`/wishlist/move-to-cart/${productId}`, { method: 'POST', body: JSON.stringify({ quantity: 1 }) });
      applyCartState({ items: data.cart || [], summary: data.summary || findCartState().summary });
      applyWishlistState({ items: data.wishlist || [], count: Number(data.wishlist_count || 0) });
      showToast(data.message || 'Moved to Cart');
    } catch (error) {
      showToast(error.message, 'error');
    } finally {
      setButtonLoading(button, false);
    }
  }

  async function saveForLater(productId, button) {
    if (!productId) return;
    try {
      const data = await requestJson(`/wishlist/add/${productId}`, { method: 'POST', body: JSON.stringify({}) });
      const cartData = await requestJson(`/cart/remove/${productId}`, { method: 'POST', body: JSON.stringify({}) });
      applyWishlistState({ items: data.wishlist || [], count: Number(data.wishlist_count || 0) });
      applyCartState({ items: cartData.cart || [], summary: cartData.summary || findCartState().summary });
      showToast('Saved for later');
    } catch (error) {
      showToast(error.message, 'error');
    }
  }

  function getQtyInput(productId) {
    return document.querySelector(`[data-cart-qty-input="${productId}"]`);
  }

  document.addEventListener('click', async (event) => {
    const wishlistButton = event.target.closest('[data-wishlist-id], .pcard-wishlist, .uc-wish, #pd-wish');
    if (wishlistButton) {
      event.preventDefault();
      event.stopPropagation();
      const productId = getProductId(wishlistButton);
      if (wishlistButton.id === 'pd-wish') {
        wishlistButton.dataset.wishlistId = wishlistButton.dataset.wishlistId || document.getElementById('pd-review-form')?.dataset.productId || '';
      }
      await toggleWishlist(productId || wishlistButton.dataset.wishlistId, wishlistButton);
      return;
    }

    const cartAddButton = event.target.closest('[data-cart-id], .qadd, .pcard-btn-add, .uc-cart, #pd-add');
    if (cartAddButton && !cartAddButton.matches('[data-cart-step], [data-cart-action]')) {
      event.preventDefault();
      event.stopPropagation();
      const productId = getProductId(cartAddButton);
      let quantity = 1;
      if (cartAddButton.id === 'pd-add') {
        const qtyInput = document.getElementById('pd-qty');
        quantity = Math.max(1, parseInt(qtyInput?.value || '1', 10) || 1);
      }
      await addToCart(productId || cartAddButton.dataset.productId, cartAddButton, quantity);
      return;
    }

    const removeCartButton = event.target.closest('[data-cart-remove]');
    if (removeCartButton) {
      event.preventDefault();
      await removeFromCart(removeCartButton.dataset.cartRemove, removeCartButton);
      return;
    }

    const saveLaterButton = event.target.closest('[data-save-later]');
    if (saveLaterButton) {
      event.preventDefault();
      await saveForLater(saveLaterButton.dataset.saveLater, saveLaterButton);
      return;
    }

    const removeWishlistButton = event.target.closest('[data-wishlist-remove]');
    if (removeWishlistButton) {
      event.preventDefault();
      await removeFromWishlist(removeWishlistButton.dataset.wishlistRemove, removeWishlistButton);
      return;
    }

    const moveToCartButton = event.target.closest('[data-move-to-cart]');
    if (moveToCartButton) {
      event.preventDefault();
      await moveWishlistToCart(moveToCartButton.dataset.moveToCart, moveToCartButton);
      return;
    }

    const qtyStepButton = event.target.closest('[data-cart-step], [data-cart-action]');
    if (qtyStepButton) {
      event.preventDefault();
      const productId = qtyStepButton.dataset.cartId;
      const input = getQtyInput(productId);
      if (!input) return;
      const action = String(qtyStepButton.dataset.cartAction || '').toLowerCase();
      const delta = action === 'decrease'
        ? -1
        : action === 'increase'
          ? 1
          : Number(qtyStepButton.dataset.cartStep || 0);
      const current = Math.max(0, parseInt(input.value || '1', 10) || 1);
      const next = Math.max(1, current + delta);
      input.value = String(next);
      await updateCart(productId, next, qtyStepButton);
    }
  });

  document.addEventListener('change', async (event) => {
    const qtyInput = event.target.closest('[data-cart-qty-input]');
    if (!qtyInput) return;
    const productId = qtyInput.dataset.cartQtyInput;
    const next = Math.max(0, parseInt(qtyInput.value || '1', 10) || 1);
    await updateCart(productId, next, qtyInput);
  });

  window.ucAddToCart = (productId, button, quantity = 1) => addToCart(productId, button, quantity);
  window.ucToggleWishlist = (productId, button) => toggleWishlist(productId, button);
  window.ucUpdateCartQuantity = (productId, quantity, button) => updateCart(productId, quantity, button);
  window.ucRemoveFromCart = (productId, button) => removeFromCart(productId, button);
  window.ucMoveWishlistToCart = (productId, button) => moveWishlistToCart(productId, button);
  window.ucSaveForLater = (productId, button) => saveForLater(productId, button);
  window.ucToast = showToast;

  document.addEventListener('DOMContentLoaded', () => {
    const html = document.documentElement;
    const savedTheme = localStorage.getItem('uc_theme');
    if (savedTheme) {
      html.dataset.theme = savedTheme;
    }

    const themeToggle = document.getElementById('themeToggle');
    if (themeToggle) {
      themeToggle.addEventListener('click', () => {
        html.dataset.theme = html.dataset.theme === 'dark' ? 'light' : 'dark';
        localStorage.setItem('uc_theme', html.dataset.theme);
      });
    }

    const nav = document.getElementById('navbar');
    if (nav) {
      window.addEventListener('scroll', () => {
        nav.classList.toggle('scrolled', window.scrollY > 10);
      }, { passive: true });
    }

    const embeddedCartState = document.getElementById('uc-cart-state')?.dataset?.cartState;
    if (embeddedCartState) {
      try {
        const parsed = JSON.parse(embeddedCartState);
        if (parsed && typeof parsed === 'object') {
          state.cart = parsed;
          window.ucCartState = parsed;
        }
      } catch (error) {
        // Leave the base fallback state in place if parsing fails.
      }
    }

    const cartState = window.ucCartState?.summary?.count !== undefined ? findCartState() : null;
    const wishlistState = window.ucWishlistState?.count !== undefined ? findWishlistState() : null;
    syncBadges(
      cartState ? cartState.summary.count : readBadgeCount('[data-cart-count]'),
      wishlistState ? wishlistState.count : readBadgeCount('[data-wishlist-count]')
    );
    renderCartPage();
    renderWishlistPage();

    document.querySelectorAll('[data-wishlist-id]').forEach((button) => {
      const active = window.ucWishlistState?.items?.some((item) => String(item.id) === String(button.dataset.wishlistId));
      if (active) setWishButtonState(button, true);
    });

    const pdWish = document.getElementById('pd-wish');
    if (pdWish && document.getElementById('pd-review-form')) {
      const productId = document.getElementById('pd-review-form')?.dataset.productId;
      if (productId) {
        pdWish.dataset.wishlistId = productId;
        const active = window.ucWishlistState?.items?.some((item) => String(item.id) === String(productId));
        if (active) setWishButtonState(pdWish, true);
      }
    }

  });
})();
