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

  // Pincode checker (frontend-ready)
  const pinInput = $('pd-pincode');
  const pinMsg = $('pd-pinmsg');
  const pinBtn = $('pd-pincheck');
  if (pinBtn && pinInput && pinMsg) {
    pinBtn.addEventListener('click', () => {
      const val = String(pinInput.value || '').trim();
      if (!/^\d{6}$/.test(val)) {
        pinMsg.textContent = 'Enter a valid 6-digit pincode.';
        pinMsg.style.color = '#991b1b';
        return;
      }
      pinMsg.textContent = `Delivery available to ${val} · ETA 2–4 days`;
      pinMsg.style.color = '#166534';
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
    form.addEventListener('submit', (e) => {
      e.preventDefault();
      const fd = new FormData(form);
      const name = String(fd.get('name') || '').trim() || 'Anonymous';
      const msg = String(fd.get('message') || '').trim();
      const rating = String(fd.get('rating') || '5').trim();
      if (!msg) return;
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
    });
  }
});

