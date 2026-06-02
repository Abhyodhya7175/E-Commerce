function $(id) { return document.getElementById(id); }

document.addEventListener('DOMContentLoaded', () => {
  // Image slider: read images from data attribute and wire navigation
  const mainWrap = $('pd-main');
  const mainImg = $('pd-main-img');
  const images = (() => {
    try {
      const raw = mainWrap?.dataset.images;
      return raw ? JSON.parse(raw) : [];
    } catch (e) {
      return [];
    }
  })();
  const thumbs = Array.from(document.querySelectorAll('.pd-thumb[data-img]'));
  let currentIndex = 0;

  function showImageAt(index){
    if (!images || images.length === 0) return;
    const idx = (index + images.length) % images.length;
    const src = images[idx];
    const main = mainImg || $('pd-main-img');
    if (!main || !src) return;
    main.src = src;
    if (thumbs && thumbs.length) {
      thumbs.forEach((b, i) => b.classList.toggle('active', i === idx));
    }
    currentIndex = idx;
  }

  if (thumbs && thumbs.length) {
    thumbs.forEach((btn, i) => {
      btn.addEventListener('click', () => showImageAt(i));
    });
  }

  // initialize to first image if present
  if (images && images.length) showImageAt(0);

  // Prev/Next buttons
  const prevBtn = document.querySelector('.pd-nav-prev');
  const nextBtn = document.querySelector('.pd-nav-next');
  if (prevBtn) prevBtn.addEventListener('click', () => showImageAt(currentIndex - 1));
  if (nextBtn) nextBtn.addEventListener('click', () => showImageAt(currentIndex + 1));

  // keyboard navigation
  document.addEventListener('keydown', (e) => {
    if (e.key === 'ArrowLeft') showImageAt(currentIndex - 1);
    if (e.key === 'ArrowRight') showImageAt(currentIndex + 1);
  });

  // touch swipe support for the main image
  if (mainWrap) {
    let touchStartX = 0;
    let touchEndX = 0;
    mainWrap.addEventListener('touchstart', (e) => {
      touchStartX = e.changedTouches[0].clientX;
    }, {passive:true});
    mainWrap.addEventListener('touchend', (e) => {
      touchEndX = e.changedTouches[0].clientX;
      const dx = touchEndX - touchStartX;
      const threshold = 40; // px
      if (dx > threshold) showImageAt(currentIndex - 1);
      else if (dx < -threshold) showImageAt(currentIndex + 1);
    }, {passive:true});
  }

  // Pincode checker
  const pinCard = $('pd-pin-card');
  const pinInput = $('pd-pincode');
  const pinMsg = $('pd-pinmsg');
  const pinBtn = $('pd-pincheck');
  const pinLoader = $('pd-pinloader');
  const codBadge = $('pd-cod-badge');
  const etaBadge = $('pd-eta-badge');
  const dateBadge = $('pd-date-badge');
  const freeShipBadge = $('pd-free-ship');

  function setPinMessage(message, status) {
    if (!pinMsg) return;
    pinMsg.textContent = message || '';
    pinMsg.classList.remove('success', 'error');
    if (status === 'success') pinMsg.classList.add('success');
    if (status === 'error') pinMsg.classList.add('error');
  }

  function setLoader(active) {
    if (pinLoader) pinLoader.hidden = !active;
    if (pinBtn) pinBtn.disabled = active;
  }

  function resetBadges() {
    [codBadge, etaBadge, dateBadge, freeShipBadge].forEach((badge) => {
      if (badge) badge.hidden = true;
    });
    if (codBadge) {
      codBadge.classList.remove('pd-badge-danger');
      codBadge.classList.add('pd-badge-success');
    }
  }

  if (pinBtn && pinInput && pinMsg) {
    pinBtn.addEventListener('click', async () => {
      const val = String(pinInput.value || '').trim();
      if (!/^[1-9]\d{5}$/.test(val)) {
        resetBadges();
        setPinMessage('Enter a valid 6-digit Indian pincode.', 'error');
        return;
      }

      const productId = pinCard?.dataset.productId || '';
      const weight = pinCard?.dataset.weight || '';
      const price = pinCard?.dataset.price || '';

      resetBadges();
      setPinMessage('', null);
      setLoader(true);

      try {
        const params = new URLSearchParams();
        if (productId) params.set('product_id', productId);
        if (weight) params.set('weight', weight);
        if (price) params.set('order_value', price);

        const response = await fetch(`/check-pincode/${encodeURIComponent(val)}?${params.toString()}`);
        let data = {};
        try {
          data = await response.json();
        } catch {
          data = {};
        }

        if (!response.ok) {
          resetBadges();
          setPinMessage(data.error || 'Unable to check delivery at the moment.', 'error');
          return;
        }

        if (!data.available) {
          setPinMessage('Delivery is not available for this pincode.', 'error');
          if (codBadge) {
            codBadge.textContent = 'COD Unavailable';
            codBadge.classList.remove('pd-badge-success');
            codBadge.classList.add('pd-badge-danger');
            codBadge.hidden = false;
          }
          return;
        }

        const courier = data.courier ? ` via ${data.courier}` : '';
        const etaText = data.eta ? ` · ETA ${data.eta}` : '';
        setPinMessage(`Delivery available${courier}${etaText}.`, 'success');

        if (data.cod && codBadge) {
          codBadge.textContent = 'COD Available';
          codBadge.hidden = false;
        } else if (codBadge) {
          codBadge.textContent = 'COD Unavailable';
          codBadge.classList.remove('pd-badge-success');
          codBadge.classList.add('pd-badge-danger');
          codBadge.hidden = false;
        }

        if (data.eta && etaBadge) {
          etaBadge.textContent = `ETA: ${data.eta}`;
          etaBadge.hidden = false;
        }

        if (data.estimated_date && dateBadge) {
          dateBadge.textContent = `Delivers by ${data.estimated_date}`;
          dateBadge.hidden = false;
        }

        if (data.free_shipping && freeShipBadge) {
          freeShipBadge.hidden = false;
        }
      } catch (error) {
        resetBadges();
        setPinMessage('Delivery check failed. Please try again.', 'error');
      } finally {
        setLoader(false);
      }
    });
  }

  // Quantity
  const qtyInput = $('pd-qty');
  const addBtn = $('pd-add');
  const availableStock = Math.max(0, parseInt(addBtn?.dataset.stock || '0', 10) || 0);
  document.querySelectorAll('.pd-qtybtn[data-qty]').forEach((btn) => {
    btn.addEventListener('click', () => {
      if (!qtyInput) return;
      const delta = parseInt(btn.dataset.qty, 10) || 0;
      const current = Math.max(1, parseInt(qtyInput.value || '1', 10) || 1);
      let next = Math.max(1, current + delta);
      if (availableStock > 0 && next > availableStock) {
        next = availableStock;
        // brief user feedback
        alert(`Only ${availableStock} unit${availableStock === 1 ? '' : 's'} available in stock.`);
      }
      qtyInput.value = String(next);
    });
  });

  if (qtyInput) {
    // Clamp manual input to valid range on blur/change
    qtyInput.addEventListener('change', () => {
      let val = Math.max(1, parseInt(qtyInput.value || '1', 10) || 1);
      if (availableStock > 0 && val > availableStock) {
        val = availableStock;
        alert(`Only ${availableStock} unit${availableStock === 1 ? '' : 's'} available in stock.`);
      }
      qtyInput.value = String(val);
    });
    qtyInput.addEventListener('input', () => {
      // prevent non-numeric and leading zeros
      qtyInput.value = qtyInput.value.replace(/[^0-9]/g, '').replace(/^0+/, '') || '1';
    });
  }

  if (addBtn && qtyInput) {
    addBtn.addEventListener('click', (e) => {
      const qty = Math.max(1, parseInt(qtyInput.value || '1', 10) || 1);
      if (availableStock > 0 && qty > availableStock) {
        e.preventDefault();
        alert(`Cannot add ${qty} items — only ${availableStock} in stock.`);
        qtyInput.value = String(availableStock);
        return;
      }
    });
  }

  // Share buttons
  document.querySelectorAll('.pd-sharebtn[data-share]').forEach((btn) => {
    btn.addEventListener('click', async () => {
      const type = btn.dataset.share;
      const url = window.location.href;
      if (type === 'native') {
        // Try native share API first
        try {
          await navigator.share({
            title: document.title || '',
            text: (document.querySelector('#pd-short-desc')?.textContent || '').trim(),
            url: url
          });
          return;
        } catch (err) {
          // fall through to copy fallback
        }
      }

      if (type === 'copy') {
        try {
          await navigator.clipboard.writeText(url);
          btn.textContent = 'Copied';
          setTimeout(() => (btn.textContent = 'Copy Link'), 1400);
        } catch {
          alert('Copy failed. Please copy from the address bar.');
        }
        return;
      }
      if (type === 'whatsapp') {
        window.open(`https://wa.me/?text=${encodeURIComponent(url)}`, '_blank');
      }
      if (type === 'facebook') {
        window.open(`https://www.facebook.com/sharer/sharer.php?u=${encodeURIComponent(url)}`, '_blank');
      }
    });
  });

  // Review star selector
  const starWrap = $('pd-star-select');
  const ratingInput = $('pd-rating');
  function setStars(value) {
    const v = Math.min(5, Math.max(1, value));
    if (ratingInput) ratingInput.value = String(v);
    starWrap?.querySelectorAll('.pd-starbtn').forEach((b) => {
      const s = parseInt(b.dataset.star || '0', 10);
      b.classList.toggle('inactive', s > v);
    });
  }
  if (starWrap) {
    starWrap.addEventListener('click', (e) => {
      const btn = e.target.closest('.pd-starbtn');
      if (!btn) return;
      const v = parseInt(btn.dataset.star || '5', 10) || 5;
      setStars(v);
    });
    setStars(parseInt(starWrap.dataset.value || '5', 10) || 5);
  }

  // Review submission (frontend-ready)
  const form = $('pd-review-form');
  const list = $('pd-review-list');
  if (form && list) {
    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      const fd = new FormData(form);
      const name = String(fd.get('name') || '').trim() || 'Anonymous';
      const msg = String(fd.get('message') || '').trim();
      const rating = String(fd.get('rating') || '5').trim();
      if (!msg) {
        alert("Please enter a message");
        return;
      }

      // Get product ID from form data attribute
      const productId = form.dataset.productId || form.getAttribute('data-product-id');
      if (!productId) {
        alert("Product ID not found");
        return;
      }

      // Send to backend
      try {
        const response = await fetch("/shop/api/reviews/add", {
          method: "POST",
          headers: {
            "Content-Type": "application/json"
          },
          body: JSON.stringify({
            product_id: parseInt(productId),
            name: name,
            message: msg,
            rating: parseInt(rating)
          })
        });

        const data = await response.json();

        if (data.success) {
          // Add to UI
          const stars = '★★★★★'.slice(0, Math.min(5, Math.max(1, parseInt(rating, 10) || 5)));
          const div = document.createElement('div');
          div.className = 'pd-review';
          div.innerHTML = `
            <div class="pd-review-head">
              <strong>${name.replace(/</g,'&lt;')}</strong>
              <span class="pd-mini-stars">${stars}</span>
            </div>
            <p>${msg.replace(/</g,'&lt;')}</p>
          `;
          list.prepend(div);
          form.reset();
          setStars(5);
          alert("Review saved successfully!");
        } else {
          alert(data.error || "Failed to save review");
        }
      } catch (error) {
        console.error("Error:", error);
        alert("Error saving review: " + error.message);
      }
    });
  }

  // Read more / Read less for short description
  (function(){
    const shortDesc = $('pd-short-desc');
    const toggle = $('pd-desc-toggle');
    const threshold = 240; // characters
    if (!shortDesc || !toggle) return;
    const text = shortDesc.textContent?.trim() || '';
    if (text.length <= threshold) {
      // nothing to toggle
      toggle.hidden = true;
      return;
    }
    // initialize collapsed
    shortDesc.classList.add('pd-desc-collapsed');
    toggle.hidden = false;
    toggle.addEventListener('click', () => {
      const expanded = toggle.getAttribute('aria-expanded') === 'true';
      if (expanded) {
        shortDesc.classList.remove('pd-desc-expanded');
        shortDesc.classList.add('pd-desc-collapsed');
        toggle.textContent = '...';
        toggle.setAttribute('aria-expanded', 'false');
      } else {
        shortDesc.classList.remove('pd-desc-collapsed');
        shortDesc.classList.add('pd-desc-expanded');
        toggle.textContent = 'Read less';
        toggle.setAttribute('aria-expanded', 'true');
      }
    });
  })();
});

