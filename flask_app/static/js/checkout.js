(function () {
  const CFG = window.ucCheckout || {};
  const TOKEN = () => document.querySelector('meta[name="csrf-token"]')?.content || window.ucCsrfToken || '';

  const state = {
    cart: CFG.cart || { items: [], summary: {} },
    addresses: CFG.addresses || [],
    selectedAddressId: null,
    couponCode: '',
    appliedCoupon: null,
    coins: 0,
    shippingMethod: 'standard',
    pincodeStatus: null,
    useNewAddress: false,
    contactEditing: false,
    loading: false,
  };

  const $ = (sel, root = document) => root.querySelector(sel);
  const $$ = (sel, root = document) => [...root.querySelectorAll(sel)];

  function money(n) {
    return '₹' + Math.round(Number(n) || 0).toLocaleString('en-IN');
  }

  async function api(url, options = {}) {
    const res = await fetch(url, {
      credentials: 'same-origin',
      headers: {
        'Content-Type': 'application/json',
        Accept: 'application/json',
        'X-CSRFToken': TOKEN(),
        ...(options.headers || {}),
      },
      ...options,
    });
    const data = await res.json().catch(() => ({}));
    return { ok: res.ok, status: res.status, data };
  }

  function setProgress(stepName) {
    const order = ['cart', 'address', 'delivery', 'payment'];
    const normalized = stepName === 'contact' ? 'address' : stepName;
    const progressIdx = order.indexOf(normalized);
    if (progressIdx < 0) return;

    $$('.co-stepper-list .co-step').forEach((el) => {
      const i = order.indexOf(el.dataset.step);
      const icon = el.querySelector('.co-step-icon');
      el.classList.remove('is-done', 'is-active');
      if (i < progressIdx) {
        el.classList.add('is-done');
        if (icon) icon.innerHTML = '<i class="fa-solid fa-check"></i>';
      } else if (i === progressIdx) {
        el.classList.add('is-active');
        if (icon) icon.textContent = String(i + 1);
      } else if (icon) {
        icon.textContent = String(i + 1);
      }
    });
    $$('.co-stepper-list .co-step-connector').forEach((conn, idx) => {
      conn.classList.toggle('is-done', progressIdx > idx);
    });
  }

  function addressTypeLabel(addr, index) {
    if (addr.isDefault) return 'Home';
    if (index === 1 || (!state.addresses.some((a) => a.isDefault) && index === 0)) return 'Office';
    return `Address ${index + 1}`;
  }

  function getContact() {
    return {
      fullName: $('#contact-fullName')?.value.trim() || '',
      email: $('#contact-email')?.value.trim() || '',
      mobile: $('#contact-mobile')?.value.trim() || '',
    };
  }

  function getSelectedAddress() {
    const useGuest =
      !CFG.isLoggedIn ||
      state.useNewAddress ||
      !state.addresses.length ||
      !state.selectedAddressId;
    if (!useGuest && state.selectedAddressId) {
      return state.addresses.find((a) => a.id === state.selectedAddressId);
    }
    const form = $('#co-guest-address-form');
    if (!form) return null;
    const fd = new FormData(form);
    const pincode = String(fd.get('pincode') || '').replace(/\D/g, '');
    if (!fd.get('house') || !pincode) return null;
    return {
      fullName: fd.get('fullName'),
      mobile: fd.get('mobile'),
      house: fd.get('house'),
      street: fd.get('street'),
      landmark: fd.get('landmark'),
      city: fd.get('city'),
      state: fd.get('state'),
      pincode,
      country: fd.get('country') || 'India',
    };
  }

  function formatAddress(addr) {
    if (!addr) return null;
    const lines = [
      [addr.fullName, addr.mobile].filter(Boolean).join(' · '),
      [addr.house, addr.street, addr.landmark].filter(Boolean).join(', '),
      [addr.city, addr.state, addr.pincode].filter(Boolean).join(', '),
      addr.country || 'India',
    ].filter(Boolean);
    return lines.join('\n');
  }

  function syncGuestFromContact() {
    const c = getContact();
    const form = $('#co-guest-address-form');
    if (!form || !c.fullName) return;
    if (form.fullName && !form.fullName.value) form.fullName.value = c.fullName;
    if (form.mobile && !form.mobile.value) form.mobile.value = c.mobile;
  }

  function updateAddressUi() {
    const guest = $('#co-guest-address');
    const toggleWrap = $('#co-use-new-address-wrap');
    const hasSaved = CFG.isLoggedIn && state.addresses.length > 0;

    if (toggleWrap) toggleWrap.classList.toggle('d-none', !hasSaved || state.useNewAddress);

    if (!CFG.isLoggedIn || !hasSaved || state.useNewAddress) {
      guest?.classList.remove('d-none');
      syncGuestFromContact();
    } else {
      guest?.classList.add('d-none');
    }
  }

  function renderAddresses() {
    const wrap = $('#co-saved-addresses');
    if (!wrap) return;
    if (!CFG.isLoggedIn) {
      wrap.innerHTML = '';
      updateAddressUi();
      return;
    }

    if (!state.addresses.length) {
      wrap.innerHTML = `
        <div class="co-address-empty">
          <p>No saved addresses yet. Add one to continue checkout.</p>
        </div>`;
      state.useNewAddress = true;
      updateAddressUi();
      return;
    }

    wrap.innerHTML = state.addresses
      .map((a, index) => {
        const selected = state.selectedAddressId === a.id && !state.useNewAddress;
        const tag = addressTypeLabel(a, index);
        const line = [a.city, a.state].filter(Boolean).join(', ');
        return `
      <label class="co-address-card ${selected ? 'is-selected' : ''}" data-addr-id="${a.id}">
        <input type="radio" name="savedAddress" value="${a.id}" ${selected ? 'checked' : ''}>
        <span class="co-address-card-inner">
          <span class="co-address-tag">${tag}${a.isDefault ? '<span class="co-badge-default">Default</span>' : ''}</span>
          <strong>${a.fullName}</strong>
          <span class="co-address-lines">${line}</span>
          <span class="co-address-phone">${a.mobile}</span>
          <span class="co-address-actions">
            <button type="button" class="co-btn co-btn-outline co-btn-sm" data-select-addr="${a.id}">Select</button>
            <button type="button" class="co-btn co-btn-ghost co-btn-sm" data-edit-addr="${a.id}">Edit</button>
            <button type="button" class="co-btn co-btn-ghost co-btn-sm" data-del-addr="${a.id}">Delete</button>
          </span>
        </span>
      </label>`;
      })
      .join('');

    if (!state.selectedAddressId && state.addresses[0] && !state.useNewAddress) {
      state.selectedAddressId = state.addresses.find((a) => a.isDefault)?.id || state.addresses[0].id;
      syncPincodeFromAddress();
    }

    wrap.querySelectorAll('.co-address-card').forEach((card) => {
      card.addEventListener('click', (e) => {
        if (e.target.closest('button')) return;
        selectAddress(Number(card.dataset.addrId));
      });
    });
    wrap.querySelectorAll('[data-select-addr]').forEach((btn) => {
      btn.addEventListener('click', (e) => {
        e.preventDefault();
        e.stopPropagation();
        selectAddress(Number(btn.dataset.selectAddr));
      });
    });
    wrap.querySelectorAll('[data-edit-addr]').forEach((btn) => {
      btn.addEventListener('click', (e) => {
        e.preventDefault();
        e.stopPropagation();
        openAddressModal(Number(btn.dataset.editAddr));
      });
    });
    wrap.querySelectorAll('[data-del-addr]').forEach((btn) => {
      btn.addEventListener('click', (e) => {
        e.preventDefault();
        e.stopPropagation();
        deleteAddress(Number(btn.dataset.delAddr));
      });
    });
    updateAddressUi();
  }

  function selectAddress(id) {
    state.selectedAddressId = id;
    state.useNewAddress = false;
    renderAddresses();
    syncPincodeFromAddress();
    refreshPreview();
  }

  function syncPincodeFromAddress() {
    const addr = state.addresses.find((a) => a.id === state.selectedAddressId);
    const pinInput = $('#co-pincode');
    if (addr?.pincode && pinInput && !pinInput.value) {
      pinInput.value = addr.pincode;
    }
  }

  function updateBreakdown(totals) {
    if (!totals) return;
    $('#bd-subtotal').textContent = money(totals.subtotal);
    $('#bd-product-disc').textContent = '-' + money(totals.productDiscount);
    $('#bd-shipping').textContent = money(totals.shippingCharges);
    $('#bd-gst').textContent = money(totals.gstTotal);
    $('#bd-grand').textContent = money(totals.grandTotal);
    $('#co-mobile-total').textContent = money(totals.grandTotal);
    $('#co-pay-amt-desktop').textContent = money(totals.grandTotal);
    const mobAmt = $('#co-pay-amt-mobile');
    const mobCtaAmt = $('#co-mobile-cta-amt');
    if (mobAmt) mobAmt.textContent = money(totals.grandTotal);
    if (mobCtaAmt) {
      mobCtaAmt.textContent = money(totals.grandTotal);
      mobCtaAmt.classList.remove('d-none');
    }
    const savings = (totals.productDiscount || 0) + (totals.couponDiscount || 0) + (totals.coinDiscount || 0);
    const strip = $('#co-savings-strip');
    if (strip && savings > 0) {
      strip.classList.remove('d-none');
      $('#co-savings-amt').textContent = money(savings);
    } else strip?.classList.add('d-none');
    if ($('#co-item-count')) $('#co-item-count').textContent = totals.itemCount || 0;

    const couponRow = $('#row-coupon');
    const coinsRow = $('#row-coins');
    const platformRow = $('#row-platform');
    if (totals.couponDiscount > 0) {
      couponRow?.classList.remove('d-none');
      $('#bd-coupon').textContent = '-' + money(totals.couponDiscount);
    } else couponRow?.classList.add('d-none');
    if (totals.coinDiscount > 0) {
      coinsRow?.classList.remove('d-none');
      $('#bd-coins').textContent = '-' + money(totals.coinDiscount);
    } else coinsRow?.classList.add('d-none');
    if (totals.platformFee > 0) {
      platformRow?.classList.remove('d-none');
      $('#bd-platform').textContent = money(totals.platformFee);
    } else platformRow?.classList.add('d-none');

    const slider = $('#co-coins-slider');
    if (slider) {
      slider.max = totals.maxRedeemableCoins || 0;
      if (state.coins > totals.maxRedeemableCoins) state.coins = totals.maxRedeemableCoins;
      slider.value = state.coins;
    }
    $('#co-coins-available') && ($('#co-coins-available').textContent = totals.availableCoins);
  }

  async function refreshPreview() {
    if (state.loading) return;
    state.loading = true;
    $('#co-cart-lines')?.classList.add('co-skeleton');
    const { ok, data } = await api(CFG.urls.preview, {
      method: 'POST',
      body: JSON.stringify({
        shippingMethod: state.shippingMethod,
        couponCode: state.couponCode,
        coinsToRedeem: state.coins,
      }),
    });
    state.loading = false;
    $('#co-cart-lines')?.classList.remove('co-skeleton');
    if (ok && data.cart) {
      state.cart = data.cart;
      if (data.appliedCoupon) state.appliedCoupon = data.appliedCoupon;
    }
    if (ok && data.totals) updateBreakdown(data.totals);
    return data;
  }

  async function applyCoupon() {
    const code = $('#co-coupon-input')?.value.trim();
    const msg = $('#co-coupon-msg');
    if (!code) return;
    const { ok, data } = await api(CFG.urls.applyCoupon, {
      method: 'POST',
      body: JSON.stringify({
        code,
        shippingMethod: state.shippingMethod,
        coinsToRedeem: state.coins,
      }),
    });
    msg?.classList.remove('d-none', 'is-error', 'is-success');
    if (!ok) {
      msg.classList.add('is-error');
      msg.textContent = data.error || 'Invalid coupon';
      return;
    }
    state.couponCode = code;
    state.appliedCoupon = data.coupon;
    msg.classList.add('is-success');
    msg.textContent = data.message || 'Coupon applied';
    const applied = $('#co-coupon-applied');
    applied?.classList.remove('d-none');
    $('#co-coupon-label').textContent = `${data.coupon.code} (−${money(data.totals.couponDiscount)})`;
    updateBreakdown(data.totals);
  }

  function removeCoupon() {
    state.couponCode = '';
    state.appliedCoupon = null;
    $('#co-coupon-input').value = '';
    $('#co-coupon-applied')?.classList.add('d-none');
    $('#co-coupon-msg')?.classList.add('d-none');
    refreshPreview();
  }

  async function checkPincode() {
    const pin = $('#co-pincode')?.value.replace(/\D/g, '');
    const msg = $('#co-pincode-msg');
    if (!pin || pin.length !== 6) {
      msg.textContent = 'Enter a valid 6-digit PIN code.';
      msg.className = 'co-pin-msg is-bad';
      return;
    }
    msg.textContent = 'Checking availability…';
    msg.className = 'co-pin-msg';
    const { ok, data } = await api(`${CFG.urls.pincode}${pin}`);
    if (!ok) {
      msg.textContent = data.error || 'Could not check PIN code.';
      msg.className = 'co-pin-msg is-bad';
      return;
    }
    state.pincodeStatus = data;
    if (data.available) {
      msg.innerHTML = `<i class="fa-solid fa-circle-check"></i> Delivery available${data.eta ? ` · ETA: ${data.eta}` : ''}${data.estimated_date ? ` · ${data.estimated_date}` : ''}`;
      msg.className = 'co-pin-msg is-ok';
    } else {
      msg.textContent = 'Delivery not available for this PIN code.';
      msg.className = 'co-pin-msg is-bad';
    }
    updateDeliveryEtas(pin);
  }

  function updateDeliveryEtas(pin) {
    const base = new Date();
    $$('.co-eta').forEach((el) => {
      const days = Number(el.dataset.etaDays || 5);
      const d = new Date(base);
      d.setDate(d.getDate() + days);
      el.textContent = `Est. delivery: ${d.toLocaleDateString('en-IN', { weekday: 'short', day: 'numeric', month: 'short' })}`;
    });
  }

  function validatePayment(method) {
    if (method === 'cod') return true;
    if (method === 'upi') {
      const upi = $('#pay-upi-id')?.value.trim();
      return upi && upi.includes('@');
    }
    if (method === 'card') {
      const num = ($('#pay-card-num')?.value || '').replace(/\s/g, '');
      const exp = $('#pay-card-exp')?.value.trim();
      const cvv = $('#pay-card-cvv')?.value.trim();
      const name = $('#pay-card-name')?.value.trim();
      return num.length >= 15 && /^\d{2}\/\d{2}$/.test(exp) && cvv.length >= 3 && name.length > 2;
    }
    return true;
  }

  async function placeOrder() {
    const contact = getContact();
    const address = getSelectedAddress();
    if (!contact.fullName || !contact.email || !contact.mobile) {
      alert('Please complete contact information.');
      jumpTo('contact');
      return;
    }
    if (!address || !address.pincode) {
      alert('Please select or enter a shipping address.');
      jumpTo('address');
      return;
    }
    const paymentMethod = $(`input[name="paymentMethod"]:checked`)?.value || 'cod';
    if (!validatePayment(paymentMethod)) {
      alert('Please complete payment details.');
      jumpTo('payment');
      return;
    }
    $('#co-processing')?.classList.remove('d-none');
    const paymentMeta = {
      upi: $('#pay-upi-id')?.value,
      cardLast4: ($('#pay-card-num')?.value || '').slice(-4),
    };
    const { ok, data } = await api(CFG.urls.placeOrder, {
      method: 'POST',
      body: JSON.stringify({
        contact,
        address,
        shippingMethod: state.shippingMethod,
        paymentMethod,
        couponCode: state.couponCode,
        coinsToRedeem: state.coins,
        estimatedDelivery: $('.co-eta')?.textContent,
        paymentMeta,
      }),
    });
    $('#co-processing')?.classList.add('d-none');
    if (!ok) {
      alert(data.error || 'Could not place order.');
      return;
    }
    window.location.href = data.redirect;
  }

  function jumpTo(section) {
    setProgress(section === 'contact' ? 'address' : section);
    const id = section === 'contact' ? 'sec-contact' : `sec-${section}`;
    document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    if (window.innerWidth < 992) {
      const panels = {
        contact: 'panel-contact',
        address: 'panel-address',
        delivery: 'panel-delivery',
        payment: 'panel-payment',
      };
      const panelId = panels[section];
      const panel = panelId && document.getElementById(panelId);
      if (panel && !panel.classList.contains('show')) {
        bootstrap.Collapse.getOrCreateInstance(panel).show();
      }
    }
  }

  function initScrollProgress() {
    const sections = [
      { el: '#sec-payment', step: 'payment' },
      { el: '#sec-delivery', step: 'delivery' },
      { el: '#sec-address', step: 'address' },
      { el: '#sec-contact', step: 'address' },
    ]
      .map((s) => ({ ...s, node: document.querySelector(s.el) }))
      .filter((s) => s.node);

    if (!sections.length || !('IntersectionObserver' in window)) return;

    const observer = new IntersectionObserver(
      (entries) => {
        const visible = entries
          .filter((e) => e.isIntersecting)
          .sort((a, b) => b.intersectionRatio - a.intersectionRatio)[0];
        if (visible) {
          const match = sections.find((s) => s.node === visible.target);
          if (match) setProgress(match.step);
        }
      },
      { rootMargin: '-20% 0px -55% 0px', threshold: [0.15, 0.35, 0.55] }
    );
    sections.forEach((s) => observer.observe(s.node));
  }

  async function cartMutation(url, body) {
    const { ok, data } = await api(url, { method: 'POST', body: JSON.stringify(body || {}) });
    if (ok && data.cart) {
      state.cart = { items: data.cart, summary: data.summary };
      location.reload();
    } else alert(data.error || 'Cart update failed');
  }

  function bindCartLines() {
    $$('[data-qty-delta]').forEach((btn) => {
      btn.addEventListener('click', () => {
        const id = btn.dataset.id;
        const input = $(`[data-qty-input="${id}"]`);
        let q = Number(input.value) + Number(btn.dataset.qtyDelta);
        q = Math.max(1, q);
        const url = CFG.urls.cartUpdate.replace(/\/0$/, `/${id}`);
        cartMutation(url, { quantity: q });
      });
    });
    $$('[data-remove]').forEach((btn) => {
      btn.addEventListener('click', () => {
        const url = CFG.urls.cartRemove.replace(/\/0$/, `/${btn.dataset.remove}`);
        cartMutation(url, {});
      });
    });
  }

  function bindPaymentPanels() {
    $$('input[name="paymentMethod"]').forEach((radio) => {
      radio.addEventListener('change', () => {
        $('#co-pay-panel-upi')?.classList.toggle('d-none', radio.value !== 'upi');
        $('#co-pay-panel-card')?.classList.toggle('d-none', radio.value !== 'card');
      });
    });
  }

  function bindShipping() {
    $$('input[name="shippingMethod"]').forEach((radio) => {
      radio.addEventListener('change', () => {
        state.shippingMethod = radio.value;
        refreshPreview();
      });
    });
  }

  const addressModal = () => document.getElementById('coAddressModal') && bootstrap.Modal.getOrCreateInstance('#coAddressModal');

  function openAddressModal(id) {
    const form = $('#co-address-modal-form');
    form?.reset();
    $('#addr-id').value = id || '';
    $('#coAddressModalTitle').textContent = id ? 'Edit address' : 'Add address';
    if (id) {
      const a = state.addresses.find((x) => x.id === id);
      if (a) {
        form.fullName.value = a.fullName;
        form.mobile.value = a.mobile;
        form.house.value = a.house;
        form.street.value = a.street;
        form.landmark.value = a.landmark || '';
        form.city.value = a.city;
        form.state.value = a.state;
        form.pincode.value = a.pincode;
        form.country.value = a.country || 'India';
        $('#addr-default').checked = a.isDefault;
      }
    }
    addressModal()?.show();
  }

  async function saveAddress() {
    const form = $('#co-address-modal-form');
    const fd = new FormData(form);
    const payload = Object.fromEntries(fd.entries());
    payload.isDefault = $('#addr-default')?.checked;
    const id = payload.addressId;
    delete payload.addressId;
    let url = CFG.urls.createAddress;
    let method = 'POST';
    if (id) {
      url = `${CFG.urls.updateAddress}/${id}`;
      method = 'PUT';
    }
    const { ok, data } = await api(url, { method, body: JSON.stringify(payload) });
    if (!ok) {
      alert(data.error || 'Could not save address');
      return;
    }
    if (id) {
      const idx = state.addresses.findIndex((a) => a.id === Number(id));
      if (idx >= 0) state.addresses[idx] = data.address;
    } else state.addresses.unshift(data.address);
    state.selectedAddressId = data.address.id;
    state.useNewAddress = false;
    renderAddresses();
    syncPincodeFromAddress();
    addressModal()?.hide();
  }

  async function deleteAddress(id) {
    if (!confirm('Delete this address?')) return;
    const { ok, data } = await api(`${CFG.urls.updateAddress}/${id}`, { method: 'DELETE' });
    if (!ok) {
      alert(data.error || 'Delete failed');
      return;
    }
    state.addresses = state.addresses.filter((a) => a.id !== id);
    if (state.selectedAddressId === id) state.selectedAddressId = null;
    if (!state.addresses.length) state.useNewAddress = true;
    renderAddresses();
  }

  function toggleContactEdit() {
    state.contactEditing = !state.contactEditing;
    const form = $('#co-contact-form');
    const btn = $('#co-edit-contact');
    form?.classList.toggle('is-editing', state.contactEditing);
    $$('#co-contact-form input').forEach((inp) => {
      if (state.contactEditing) inp.removeAttribute('readonly');
      else inp.setAttribute('readonly', 'readonly');
    });
    if (btn) btn.textContent = state.contactEditing ? 'Done' : 'Edit';
  }

  function trackAbandonment(step) {
    api(CFG.urls.track, {
      method: 'POST',
      body: JSON.stringify({ step, email: $('#contact-email')?.value }),
    }).catch(() => {});
  }

  function init() {
    renderAddresses();
    bindCartLines();
    bindPaymentPanels();
    bindShipping();
    updateDeliveryEtas();
    refreshPreview();
    setProgress('address');
    initScrollProgress();

    $('#co-coupon-apply')?.addEventListener('click', applyCoupon);
    $('#co-coupon-remove')?.addEventListener('click', removeCoupon);
    $('#co-pincode-btn')?.addEventListener('click', checkPincode);
    $('#co-place-order-desktop')?.addEventListener('click', placeOrder);
    $('#co-place-order-mobile')?.addEventListener('click', placeOrder);
    $$('#co-add-address-btn, #co-add-address-btn-mobile').forEach((btn) => {
      btn.addEventListener('click', () => openAddressModal());
    });
    $('#co-save-address')?.addEventListener('click', saveAddress);
    $('#co-edit-contact')?.addEventListener('click', toggleContactEdit);
    $('#co-toggle-new-address')?.addEventListener('click', () => {
      state.useNewAddress = !state.useNewAddress;
      if (state.useNewAddress) state.selectedAddressId = null;
      renderAddresses();
      updateAddressUi();
    });

    const slider = $('#co-coins-slider');
    slider?.addEventListener('input', () => {
      state.coins = Number(slider.value);
      refreshPreview();
    });
    $$('.co-coin-preset').forEach((btn) => {
      btn.addEventListener('click', () => {
        state.coins = Number(btn.dataset.coins);
        slider.value = state.coins;
        refreshPreview();
      });
    });
    $('#co-coins-max')?.addEventListener('click', () => {
      state.coins = Number(slider.max);
      slider.value = state.coins;
      refreshPreview();
    });

    ['#contact-fullName', '#contact-email', '#contact-mobile'].forEach((sel) => {
      $(sel)?.addEventListener('blur', syncGuestFromContact);
    });

    let abandonStep = 'address';
    const syncAbandonStep = () => {
      const payment = $('#sec-payment');
      const delivery = $('#sec-delivery');
      if (payment && payment.getBoundingClientRect().top < window.innerHeight * 0.45) abandonStep = 'payment';
      else if (delivery && delivery.getBoundingClientRect().top < window.innerHeight * 0.45) abandonStep = 'delivery';
      else abandonStep = 'address';
    };
    window.addEventListener('scroll', syncAbandonStep, { passive: true });
    window.addEventListener('beforeunload', () => trackAbandonment(abandonStep));
    setInterval(() => trackAbandonment(abandonStep), 60000);
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();
})();
