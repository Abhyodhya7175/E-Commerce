function $(id) { return document.getElementById(id); }

document.addEventListener('DOMContentLoaded', () => {
  // Thumbnail switching
  document.querySelectorAll('.pd-thumb[data-img]').forEach((btn) => {
    btn.addEventListener('click', () => {
      const img = btn.dataset.img;
      const main = $('pd-main-img');
      if (!main || !img) return;
      main.src = img;
      document.querySelectorAll('.pd-thumb').forEach(b => b.classList.toggle('active', b === btn));
    });
  });

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
  document.querySelectorAll('.pd-qtybtn[data-qty]').forEach((btn) => {
    btn.addEventListener('click', () => {
      if (!qtyInput) return;
      const delta = parseInt(btn.dataset.qty, 10) || 0;
      const current = Math.max(1, parseInt(qtyInput.value || '1', 10) || 1);
      qtyInput.value = String(Math.max(1, current + delta));
    });
  });

  // Share buttons
  document.querySelectorAll('.pd-sharebtn[data-share]').forEach((btn) => {
    btn.addEventListener('click', async () => {
      const type = btn.dataset.share;
      const url = window.location.href;
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
});

