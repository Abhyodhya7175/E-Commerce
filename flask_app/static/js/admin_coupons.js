(function () {
  const CFG = window.ucCouponAdmin || { urls: {} };
  const state = {
    page: 1,
    perPage: 12,
    lookup: { products: [], categories: [], brands: [] },
    assignments: {
      productIds: [],
      categoryIds: [],
      brandIds: [],
      excludeProductIds: [],
      excludeCategoryIds: [],
    },
    rules: [],
    charts: { usage: null, revenue: null },
  };

  const $ = (id) => document.getElementById(id);
  const money = (n) => '₹' + Math.round(Number(n) || 0).toLocaleString('en-IN');

  async function api(url, options = {}) {
    const res = await fetch(url, {
      credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json', Accept: 'application/json', ...(options.headers || {}) },
      ...options,
    });
    const data = await res.json().catch(() => ({}));
    return { ok: res.ok, data };
  }

  function toast(msg, isError) {
    const el = $('cpToast');
    if (!el) return;
    el.textContent = msg;
    el.className = 'cp-toast show' + (isError ? ' error' : '');
    setTimeout(() => el.classList.remove('show'), 3200);
  }

  function badgeClass(status) {
    return `cp-badge cp-badge-${status}`;
  }

  function formatDate(iso) {
    if (!iso) return '—';
    try {
      return new Date(iso).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' });
    } catch {
      return '—';
    }
  }

  function splitIso(iso) {
    if (!iso) return { date: '', time: '00:00' };
    const d = new Date(iso);
    const date = d.toISOString().slice(0, 10);
    const time = d.toTimeString().slice(0, 5);
    return { date, time };
  }

  async function loadStats() {
    const { ok, data } = await api(CFG.urls.stats);
    if (!ok || !data.stats) return;
    const s = data.stats;
    $('statActive').textContent = s.activeCoupons;
    $('statScheduled').textContent = s.scheduledPromotions;
    $('statRevenue').textContent = money(s.revenueGenerated);
    $('statDiscounts').textContent = money(s.totalDiscounts);
    $('statRedemption').textContent = s.redemptionRate + '%';
    $('statAov').textContent = (s.aovImpact >= 0 ? '+' : '') + money(s.aovImpact);
  }

  async function loadTable() {
    const q = $('cpTableSearch')?.value || '';
    const status = $('cpStatusFilter')?.value || '';
    const sort = $('cpTableSort')?.value || 'created_desc';
    const url = `${CFG.urls.list}?q=${encodeURIComponent(q)}&status=${status}&page=${state.page}&perPage=${state.perPage}&sort=${sort}`;
    const { ok, data } = await api(url);
    if (!ok) return;
    const tbody = $('cpCouponsBody');
    if (!tbody) return;
    tbody.innerHTML = (data.items || [])
      .map(
        (c) => `
      <tr data-id="${c.id}">
        <td><input type="checkbox" class="cp-row-check" value="${c.id}"></td>
        <td>${escapeHtml(c.name)}</td>
        <td><code>${escapeHtml(c.code)}</code></td>
        <td>${escapeHtml(c.discountType)}</td>
        <td>${c.usedCount}${c.usageLimit ? '/' + c.usageLimit : ''}</td>
        <td>${formatDate(c.startsAt)}</td>
        <td>${formatDate(c.expiresAt)}</td>
        <td><span class="${badgeClass(c.status)}">${c.status}</span></td>
        <td>
          <button type="button" class="cp-btn cp-btn-outline cp-btn-sm" data-edit="${c.id}">Edit</button>
          <button type="button" class="cp-btn cp-btn-outline cp-btn-sm" data-dup="${c.id}">Dup</button>
          <button type="button" class="cp-btn cp-btn-danger cp-btn-sm" data-del="${c.id}">Del</button>
        </td>
      </tr>`
      )
      .join('');
    $('cpPageInfo').textContent = `Page ${data.page} of ${data.pages} (${data.total} total)`;
    tbody.querySelectorAll('[data-edit]').forEach((b) => b.addEventListener('click', () => loadCoupon(Number(b.dataset.edit))));
    tbody.querySelectorAll('[data-dup]').forEach((b) => b.addEventListener('click', () => duplicateCoupon(Number(b.dataset.dup))));
    tbody.querySelectorAll('[data-del]').forEach((b) => b.addEventListener('click', () => deleteCoupon(Number(b.dataset.del))));
  }

  function escapeHtml(s) {
    const d = document.createElement('div');
    d.textContent = s ?? '';
    return d.innerHTML;
  }

  function resetForm(kind = 'coupon') {
    $('cpId').value = '';
    $('cpKind').value = kind;
    $('cpName').value = '';
    $('cpCode').value = '';
    $('cpDescription').value = '';
    $('cpDiscountType').value = 'percent';
    $('cpDiscountValue').value = '10';
    $('cpMaxDiscount').value = '';
    $('cpMinOrder').value = '0';
    $('cpBuyX').value = '';
    $('cpBuyY').value = '';
    $('cpUsageLimit').value = '';
    $('cpPerCustomer').value = '';
    $('cpStartDate').value = '';
    $('cpStartTime').value = '00:00';
    $('cpEndDate').value = '';
    $('cpEndTime').value = '23:59';
    $('cpActive').checked = true;
    $('cpDraft').checked = false;
    $('cpFirstPurchase').checked = false;
    $('cpNewCustomer').checked = false;
    state.rules = [];
    state.assignments = { productIds: [], categoryIds: [], brandIds: [], excludeProductIds: [], excludeCategoryIds: [] };
    renderRules();
    renderAllChips();
    $('cpEditorTitle').textContent = kind === 'promotion' ? 'Promotion editor' : 'Coupon editor';
    updateDiscountFields();
  }

  function collectForm() {
    return {
      id: $('cpId').value || null,
      kind: $('cpKind').value,
      name: $('cpName').value.trim(),
      code: $('cpCode').value.trim(),
      description: $('cpDescription').value.trim(),
      discountType: $('cpDiscountType').value,
      discountValue: Number($('cpDiscountValue').value),
      maxDiscount: $('cpMaxDiscount').value || null,
      minOrderAmount: Number($('cpMinOrder').value || 0),
      buyX: $('cpBuyX').value || null,
      buyY: $('cpBuyY').value || null,
      usageLimit: $('cpUsageLimit').value || null,
      perCustomerLimit: $('cpPerCustomer').value || null,
      firstPurchaseOnly: $('cpFirstPurchase').checked,
      newCustomerOnly: $('cpNewCustomer').checked,
      active: $('cpActive').checked,
      isDraft: $('cpDraft').checked,
      startDate: $('cpStartDate').value,
      startTime: $('cpStartTime').value,
      endDate: $('cpEndDate').value,
      endTime: $('cpEndTime').value,
      rules: state.rules,
      productIds: state.assignments.productIds,
      categoryIds: state.assignments.categoryIds,
      brandIds: state.assignments.brandIds,
      excludeProductIds: state.assignments.excludeProductIds,
      excludeCategoryIds: state.assignments.excludeCategoryIds,
      flashSale: {
        name: $('cpFlashName').value,
        bannerUrl: $('cpFlashBanner').value,
        start: $('cpFlashStart').value,
        end: $('cpFlashEnd').value,
        qtyLimitPerUser: $('cpFlashQtyLimit').value,
        productIds: getFlashSelectedIds(),
      },
    };
  }

  function getFlashSelectedIds() {
    return [...document.querySelectorAll('#cpFlashProducts input:checked')].map((i) => Number(i.value));
  }

  async function saveCoupon() {
    const payload = collectForm();
    if (!payload.code) {
      toast('Coupon code is required', true);
      return;
    }
    const { ok, data } = await api(CFG.urls.save, { method: 'POST', body: JSON.stringify(payload) });
    if (!ok) {
      toast(data.error || 'Save failed', true);
      return;
    }
    toast('Coupon saved');
    $('cpId').value = data.coupon.id;
    loadStats();
    loadTable();
  }

  async function loadCoupon(id) {
    const { ok, data } = await api(`${CFG.urls.get}/${id}`);
    if (!ok) {
      toast(data.error || 'Not found', true);
      return;
    }
    const c = data.coupon;
    $('cpId').value = c.id;
    $('cpKind').value = c.kind || 'coupon';
    $('cpName').value = c.name || '';
    $('cpCode').value = c.code || '';
    $('cpDescription').value = c.description || '';
    $('cpDiscountType').value = c.discountType || 'percent';
    $('cpDiscountValue').value = c.discountValue ?? 0;
    $('cpMaxDiscount').value = c.maxDiscount ?? '';
    $('cpMinOrder').value = c.minOrderAmount ?? 0;
    $('cpBuyX').value = c.buyX ?? '';
    $('cpBuyY').value = c.buyY ?? '';
    $('cpUsageLimit').value = c.usageLimit ?? '';
    $('cpPerCustomer').value = c.perCustomerLimit ?? '';
    $('cpActive').checked = c.active;
    $('cpDraft').checked = c.isDraft;
    $('cpFirstPurchase').checked = c.firstPurchaseOnly;
    $('cpNewCustomer').checked = c.newCustomerOnly;
    const st = splitIso(c.startsAt);
    const en = splitIso(c.expiresAt);
    $('cpStartDate').value = st.date;
    $('cpStartTime').value = st.time;
    $('cpEndDate').value = en.date;
    $('cpEndTime').value = en.time;
    state.rules = c.rules || [];
    state.assignments = {
      productIds: c.productIds || [],
      categoryIds: c.categoryIds || [],
      brandIds: c.brandIds || [],
      excludeProductIds: c.excludeProductIds || [],
      excludeCategoryIds: c.excludeCategoryIds || [],
    };
    const fs = c.flashSale || {};
    $('cpFlashName').value = fs.name || '';
    $('cpFlashBanner').value = fs.bannerUrl || '';
    $('cpFlashStart').value = fs.start || '';
    $('cpFlashEnd').value = fs.end || '';
    $('cpFlashQtyLimit').value = fs.qtyLimitPerUser || '';
    renderRules();
    renderAllChips();
    syncFlashChecks(fs.productIds || []);
    $('cpEditorTitle').textContent = `Editing: ${c.code}`;
    updateDiscountFields();
    updateCountdown();
    document.getElementById('cpEditorCard')?.scrollIntoView({ behavior: 'smooth' });
  }

  function syncFlashChecks(ids) {
    document.querySelectorAll('#cpFlashProducts input').forEach((inp) => {
      inp.checked = ids.includes(Number(inp.value));
    });
  }

  async function duplicateCoupon(id) {
    const { ok, data } = await api(`${CFG.urls.duplicate}/${id}`, { method: 'POST' });
    if (!ok) {
      toast(data.error || 'Duplicate failed', true);
      return;
    }
    toast('Coupon duplicated');
    loadTable();
    loadCoupon(data.coupon.id);
  }

  async function deleteCoupon(id) {
    if (!confirm('Delete this coupon?')) return;
    const { ok, data } = await api(`${CFG.urls.delete}/${id}`, { method: 'POST' });
    if (!ok) {
      toast(data.error || 'Delete failed', true);
      return;
    }
    toast('Deleted');
    resetForm();
    loadStats();
    loadTable();
  }

  function renderRules() {
    const wrap = $('cpRulesList');
    if (!wrap) return;
    wrap.innerHTML = state.rules
      .map(
        (r, i) => `
      <div class="cp-rule" data-idx="${i}">
        <div class="cp-rule-row">
          <div class="cp-field"><label>IF field</label>
            <select data-k="field">
              <option value="cart_value" ${r.field === 'cart_value' ? 'selected' : ''}>Cart value</option>
              <option value="category" ${r.field === 'category' ? 'selected' : ''}>Category</option>
              <option value="customer_tier" ${r.field === 'customer_tier' ? 'selected' : ''}>Customer tier</option>
            </select>
          </div>
          <div class="cp-field"><label>Operator</label>
            <select data-k="op">
              <option value="gt" ${r.op === 'gt' ? 'selected' : ''}>&gt;</option>
              <option value="eq" ${r.op === 'eq' ? 'selected' : ''}>=</option>
            </select>
          </div>
          <div class="cp-field"><label>Value</label><input data-k="value" value="${escapeHtml(r.value || '')}"></div>
          <div class="cp-field"><label>THEN</label>
            <select data-k="action">
              <option value="percent" ${r.action === 'percent' ? 'selected' : ''}>% discount</option>
              <option value="fixed" ${r.action === 'fixed' ? 'selected' : ''}>₹ discount</option>
              <option value="free_shipping" ${r.action === 'free_shipping' ? 'selected' : ''}>Free shipping</option>
            </select>
          </div>
          <div class="cp-field"><label>Amount</label><input data-k="amount" type="number" value="${r.amount || ''}"></div>
          <button type="button" class="cp-btn cp-btn-danger cp-btn-sm" data-rm="${i}">×</button>
        </div>
      </div>`
      )
      .join('');
    wrap.querySelectorAll('[data-rm]').forEach((btn) => {
      btn.addEventListener('click', () => {
        state.rules.splice(Number(btn.dataset.rm), 1);
        renderRules();
      });
    });
    wrap.querySelectorAll('.cp-rule').forEach((card) => {
      const idx = Number(card.dataset.idx);
      card.querySelectorAll('[data-k]').forEach((el) => {
        el.addEventListener('change', () => syncRuleFromDom(idx, card));
        el.addEventListener('input', () => syncRuleFromDom(idx, card));
      });
    });
  }

  function syncRuleFromDom(idx, card) {
    const r = {};
    card.querySelectorAll('[data-k]').forEach((el) => {
      r[el.dataset.k] = el.value;
    });
    state.rules[idx] = r;
  }

  function addRule() {
    state.rules.push({ field: 'cart_value', op: 'gt', value: '2000', action: 'percent', amount: '10' });
    renderRules();
  }

  function fillSelect(sel, items, key = 'name') {
    if (!sel) return;
    sel.innerHTML = items.map((i) => `<option value="${i.id}">${escapeHtml(i[key])}</option>`).join('');
  }

  async function loadLookup() {
    const { ok, data } = await api(CFG.urls.lookup);
    if (!ok) return;
    state.lookup = data;
    fillSelect($('cpSelectProduct'), data.products);
    fillSelect($('cpSelectExProduct'), data.products);
    fillSelect($('cpSelectCategory'), data.categories);
    fillSelect($('cpSelectExCategory'), data.categories);
    fillSelect($('cpSelectBrand'), data.brands);
    const flash = $('cpFlashProducts');
    if (flash) {
      flash.innerHTML = data.products
        .map((p) => `<label><input type="checkbox" value="${p.id}"> ${escapeHtml(p.name)}</label>`)
        .join('');
    }
    bindMultiSelects();
  }

  function bindMultiSelects() {
    const map = [
      ['cpSelectProduct', 'productIds', 'cpChipsProducts', 'products'],
      ['cpSelectCategory', 'categoryIds', 'cpChipsCategories', 'categories'],
      ['cpSelectBrand', 'brandIds', 'cpChipsBrands', 'brands'],
      ['cpSelectExProduct', 'excludeProductIds', 'cpChipsExProducts', 'products'],
      ['cpSelectExCategory', 'excludeCategoryIds', 'cpChipsExCategories', 'categories'],
    ];
    map.forEach(([selId, key, chipId, lookupKey]) => {
      const sel = $(selId);
      if (!sel) return;
      sel.addEventListener('dblclick', () => {
        [...sel.selectedOptions].forEach((opt) => {
          const id = Number(opt.value);
          if (!state.assignments[key].includes(id)) state.assignments[key].push(id);
        });
        renderChips(chipId, key, lookupKey);
      });
    });
  }

  function renderAllChips() {
    renderChips('cpChipsProducts', 'productIds', 'products');
    renderChips('cpChipsCategories', 'categoryIds', 'categories');
    renderChips('cpChipsBrands', 'brandIds', 'brands');
    renderChips('cpChipsExProducts', 'excludeProductIds', 'products');
    renderChips('cpChipsExCategories', 'excludeCategoryIds', 'categories');
  }

  function renderChips(containerId, key, lookupKey) {
    const wrap = $(containerId);
    if (!wrap) return;
    const items = state.lookup[lookupKey] || [];
    wrap.innerHTML = state.assignments[key]
      .map((id) => {
        const item = items.find((x) => x.id === id);
        const label = item ? item.name : `#${id}`;
        return `<span class="cp-chip">${escapeHtml(label)}<button type="button" data-id="${id}" data-key="${key}">×</button></span>`;
      })
      .join('');
    wrap.querySelectorAll('button').forEach((btn) => {
      btn.addEventListener('click', () => {
        const id = Number(btn.dataset.id);
        state.assignments[btn.dataset.key] = state.assignments[btn.dataset.key].filter((x) => x !== id);
        renderChips(containerId, key, lookupKey);
      });
    });
  }

  function updateDiscountFields() {
    const t = $('cpDiscountType').value;
    $('cpBuyXWrap').style.display = t === 'buy_x_get_y' ? '' : 'none';
    $('cpBuyYWrap').style.display = t === 'buy_x_get_y' ? '' : 'none';
  }

  function updateCountdown() {
    const el = $('cpFlashCountdown');
    const end = $('cpFlashEnd').value;
    if (!el || !end) {
      if (el) el.textContent = 'Set sale dates to preview countdown';
      return;
    }
    const diff = new Date(end) - new Date();
    if (diff <= 0) {
      el.textContent = 'Sale ended';
      return;
    }
    const d = Math.floor(diff / 86400000);
    const h = Math.floor((diff % 86400000) / 3600000);
    const m = Math.floor((diff % 3600000) / 60000);
    const s = Math.floor((diff % 60000) / 1000);
    el.textContent = `${d}d ${h}h ${m}m ${s}s remaining`;
  }

  async function loadAnalytics() {
    const from = $('cpAnalyticsFrom')?.value || '';
    const to = $('cpAnalyticsTo')?.value || '';
    const url = `${CFG.urls.analytics}?from=${from}&to=${to}`;
    const { ok, data } = await api(url);
    if (!ok) return;
    const a = data.analytics;
    $('cpConvRate').textContent = a.conversionRate + '%';
    $('cpAcq').textContent = a.customerAcquisition;
    const tbody = $('cpTopCouponsTable')?.querySelector('tbody');
    if (tbody) {
      tbody.innerHTML = (a.usage || [])
        .map((u) => `<tr><td>${escapeHtml(u.code)}</td><td>${u.count}</td><td>${money(u.revenue)}</td></tr>`)
        .join('');
    }
    renderCharts(a.chart || {});
  }

  function renderCharts(chart) {
    const labels = chart.labels || [];
    if (typeof Chart === 'undefined') return;
    if (state.charts.usage) state.charts.usage.destroy();
    if (state.charts.revenue) state.charts.revenue.destroy();
    state.charts.usage = new Chart($('cpChartUsage'), {
      type: 'line',
      data: { labels, datasets: [{ label: 'Coupon usage', data: chart.usage || [], borderColor: '#1a1a2e', tension: 0.3 }] },
      options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } } },
    });
    state.charts.revenue = new Chart($('cpChartRevenue'), {
      type: 'bar',
      data: { labels, datasets: [{ label: 'Revenue', data: chart.revenue || [], backgroundColor: '#c9a84c' }] },
      options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } } },
    });
  }

  async function bulkGenerate() {
    const payload = {
      prefix: $('cpBulkPrefix').value,
      count: Number($('cpBulkCount').value),
      discountType: $('cpBulkType').value,
      discountValue: Number($('cpBulkValue').value),
      expiryDate: $('cpBulkExpiry').value,
    };
    const { ok, data } = await api(CFG.urls.bulkGenerate, { method: 'POST', body: JSON.stringify(payload) });
    if (!ok) {
      toast(data.error || 'Generate failed', true);
      return;
    }
    toast(`Generated ${data.count} coupons`);
    const tbody = $('cpBulkTable')?.querySelector('tbody');
    if (tbody) tbody.innerHTML = (data.codes || []).map((c) => `<tr><td><code>${c}</code></td></tr>`).join('');
    loadStats();
    loadTable();
  }

  async function applyBulk() {
    const action = $('cpBulkAction').value;
    if (!action) return;
    const ids = [...document.querySelectorAll('.cp-row-check:checked')].map((c) => Number(c.value));
    if (!ids.length) {
      toast('Select coupons first', true);
      return;
    }
    if (action === 'delete' && !confirm('Delete selected coupons?')) return;
    const { ok, data } = await api(CFG.urls.bulkAction, { method: 'POST', body: JSON.stringify({ action, ids }) });
    if (!ok) {
      toast(data.error || 'Bulk action failed', true);
      return;
    }
    toast('Bulk action applied');
    loadTable();
    loadStats();
  }

  async function loadRewards() {
    const { ok, data } = await api(CFG.urls.loyalty);
    if (!ok) return;
    const wrap = $('cpRewardsList');
    if (!wrap) return;
    wrap.innerHTML = (data.rewards || [])
      .map(
        (r) => `
      <div class="cp-reward-card">
        <div>
          <strong>${escapeHtml(r.title)}</strong>
          <p class="cp-subtitle">${r.coinsRequired} coins · ${r.rewardType} · ${r.rewardValue ?? '—'}</p>
        </div>
        <div>
          <button type="button" class="cp-btn cp-btn-outline cp-btn-sm" data-edit-reward="${r.id}">Edit</button>
          <button type="button" class="cp-btn cp-btn-danger cp-btn-sm" data-del-reward="${r.id}">Del</button>
        </div>
      </div>`
      )
      .join('');
    wrap.querySelectorAll('[data-edit-reward]').forEach((b) => {
      b.addEventListener('click', () => {
        const r = data.rewards.find((x) => x.id === Number(b.dataset.editReward));
        if (!r) return;
        $('cpRewardForm').classList.remove('cp-editor-hidden');
        $('cpRewardId').value = r.id;
        $('cpRewardTitle').value = r.title;
        $('cpRewardCoins').value = r.coinsRequired;
        $('cpRewardType').value = r.rewardType;
        $('cpRewardValue').value = r.rewardValue ?? '';
        $('cpRewardExpiry').value = r.expiryDays ?? '';
      });
    });
    wrap.querySelectorAll('[data-del-reward]').forEach((b) => {
      b.addEventListener('click', async () => {
        if (!confirm('Delete reward?')) return;
        await api(`${CFG.urls.loyaltyDelete}/${b.dataset.delReward}`, { method: 'POST' });
        loadRewards();
      });
    });
  }

  async function saveReward() {
    const payload = {
      id: $('cpRewardId').value || null,
      title: $('cpRewardTitle').value,
      coinsRequired: $('cpRewardCoins').value,
      rewardType: $('cpRewardType').value,
      rewardValue: $('cpRewardValue').value,
      expiryDays: $('cpRewardExpiry').value,
      active: true,
    };
    const { ok, data } = await api(CFG.urls.loyaltySave, { method: 'POST', body: JSON.stringify(payload) });
    if (!ok) {
      toast(data.error || 'Save failed', true);
      return;
    }
    toast('Reward saved');
    $('cpRewardForm').classList.add('cp-editor-hidden');
    loadRewards();
  }

  function bindTabs() {
    document.querySelectorAll('#cpFormTabs .cp-tab').forEach((tab) => {
      tab.addEventListener('click', () => {
        document.querySelectorAll('#cpFormTabs .cp-tab').forEach((t) => t.classList.remove('active'));
        document.querySelectorAll('.cp-panel').forEach((p) => p.classList.remove('active'));
        tab.classList.add('active');
        document.querySelector(`.cp-panel[data-panel="${tab.dataset.tab}"]`)?.classList.add('active');
      });
    });
  }

  function init() {
    bindTabs();
    resetForm();
    loadStats();
    loadLookup();
    loadTable();
    loadAnalytics();
    loadRewards();

    $('cpBtnSave')?.addEventListener('click', saveCoupon);
    $('cpBtnNew')?.addEventListener('click', () => resetForm($('cpKind').value));
    $('cpBtnCreateCoupon')?.addEventListener('click', () => {
      resetForm('coupon');
      document.getElementById('cpEditorCard')?.scrollIntoView({ behavior: 'smooth' });
    });
    $('cpBtnCreatePromotion')?.addEventListener('click', () => {
      resetForm('promotion');
      document.getElementById('cpEditorCard')?.scrollIntoView({ behavior: 'smooth' });
    });
    $('cpAddRule')?.addEventListener('click', addRule);
    $('cpDiscountType')?.addEventListener('change', updateDiscountFields);
    $('cpBulkGenerate')?.addEventListener('click', bulkGenerate);
    $('cpApplyBulk')?.addEventListener('click', applyBulk);
    $('cpRefreshAnalytics')?.addEventListener('click', loadAnalytics);
    $('cpAddReward')?.addEventListener('click', () => $('cpRewardForm').classList.remove('cp-editor-hidden'));
    $('cpSaveReward')?.addEventListener('click', saveReward);

    let searchTimer;
    $('cpTableSearch')?.addEventListener('input', () => {
      clearTimeout(searchTimer);
      searchTimer = setTimeout(() => {
        state.page = 1;
        loadTable();
      }, 300);
    });
    $('cpStatusFilter')?.addEventListener('change', () => {
      state.page = 1;
      loadTable();
    });
    $('cpTableSort')?.addEventListener('change', loadTable);
    $('cpPrevPage')?.addEventListener('click', () => {
      if (state.page > 1) {
        state.page--;
        loadTable();
      }
    });
    $('cpNextPage')?.addEventListener('click', () => {
      state.page++;
      loadTable();
    });
    $('cpSelectAll')?.addEventListener('change', (e) => {
      document.querySelectorAll('.cp-row-check').forEach((c) => (c.checked = e.target.checked));
    });

    $('cpFlashStart')?.addEventListener('change', updateCountdown);
    $('cpFlashEnd')?.addEventListener('change', updateCountdown);
    setInterval(updateCountdown, 1000);

    const today = new Date();
    const monthAgo = new Date(today);
    monthAgo.setDate(monthAgo.getDate() - 30);
    if ($('cpAnalyticsFrom')) $('cpAnalyticsFrom').value = monthAgo.toISOString().slice(0, 10);
    if ($('cpAnalyticsTo')) $('cpAnalyticsTo').value = today.toISOString().slice(0, 10);
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();
})();
