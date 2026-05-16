(function () {
  const listEl = document.getElementById('banner-list');
  const modal = document.getElementById('banner-modal');
  const form = document.getElementById('banner-form');
  const uploadZone = document.getElementById('upload-zone');
  const imageInput = document.getElementById('banner-image');
  const previewWrap = document.getElementById('upload-preview');
  const previewImg = document.getElementById('preview-img');
  const modalTitle = document.getElementById('banner-modal-title');
  const bannerIdInput = document.getElementById('banner-id');
  const toastEl = document.getElementById('banner-toast');

  if (!listEl || !form) return;

  let banners = [];
  let dragId = null;

  function showToast(message, isError) {
    if (!toastEl) return;
    toastEl.textContent = message;
    toastEl.className = 'flash ' + (isError ? 'flash-error' : 'flash-success');
    toastEl.hidden = false;
    setTimeout(() => { toastEl.hidden = true; }, 3500);
  }

  function statusBadge(status) {
    const labels = {
      live: ['Live', 'badge-live'],
      scheduled: ['Scheduled', 'badge-scheduled'],
      expired: ['Expired', 'badge-expired'],
      inactive: ['Inactive', 'badge-inactive'],
    };
    const [text, cls] = labels[status] || ['Unknown', 'badge-inactive'];
    return `<span class="badge ${cls}">${text}</span>`;
  }

  function formatDates(start, end) {
    const parts = [];
    if (start) parts.push(`From ${start.replace('T', ' ')}`);
    if (end) parts.push(`Until ${end.replace('T', ' ')}`);
    return parts.join(' · ') || 'No schedule limits';
  }

  function renderList(items) {
    banners = items;
    if (!items.length) {
      listEl.innerHTML = '<div class="banner-empty"><p>No banners yet. Create your first offer banner to show on the homepage.</p></div>';
      return;
    }

    listEl.innerHTML = items.map((banner) => {
      const status = banner.scheduleStatus || (banner.active ? 'live' : 'inactive');
      return `
        <article class="banner-row" draggable="true" data-id="${banner.id}">
          <div class="banner-drag" title="Drag to reorder">⋮⋮</div>
          <div class="banner-thumb"><img src="${banner.image}" alt="${banner.title}"></div>
          <div class="banner-meta">
            <h4>${banner.title}</h4>
            <p>${banner.subtitle || 'No subtitle'}</p>
            <div class="dates">${formatDates(banner.startDate, banner.endDate)}</div>
            <div style="margin-top:0.4rem;">${statusBadge(status)}</div>
          </div>
          <div class="banner-actions">
            <button type="button" class="btn-sm" data-action="edit" data-id="${banner.id}">Edit</button>
            <button type="button" class="btn-sm" data-action="toggle" data-id="${banner.id}">${banner.active ? 'Deactivate' : 'Activate'}</button>
            <button type="button" class="btn-sm danger" data-action="delete" data-id="${banner.id}">Delete</button>
          </div>
        </article>
      `;
    }).join('');

    listEl.querySelectorAll('.banner-row').forEach(bindDragRow);
    listEl.querySelectorAll('[data-action]').forEach((btn) => {
      btn.addEventListener('click', onRowAction);
    });
  }

  function bindDragRow(row) {
    row.addEventListener('dragstart', () => {
      dragId = Number(row.dataset.id);
      row.classList.add('dragging');
    });
    row.addEventListener('dragend', () => {
      dragId = null;
      row.classList.remove('dragging');
      listEl.querySelectorAll('.banner-row').forEach((el) => el.classList.remove('drag-over'));
    });
    row.addEventListener('dragover', (event) => {
      event.preventDefault();
      row.classList.add('drag-over');
    });
    row.addEventListener('dragleave', () => row.classList.remove('drag-over'));
    row.addEventListener('drop', async (event) => {
      event.preventDefault();
      row.classList.remove('drag-over');
      const targetId = Number(row.dataset.id);
      if (!dragId || dragId === targetId) return;

      const ids = banners.map((b) => b.id);
      const from = ids.indexOf(dragId);
      const to = ids.indexOf(targetId);
      ids.splice(from, 1);
      ids.splice(to, 0, dragId);

      const res = await fetch('/admin/api/banners/reorder', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ orderedIds: ids }),
      });
      const data = await res.json();
      if (!res.ok) {
        showToast(data.error || 'Could not reorder banners', true);
        return;
      }
      renderList(enrichBanners(data.banners));
    });
  }

  function enrichBanners(items) {
    const now = new Date();
    return items.map((banner) => {
      let scheduleStatus = 'inactive';
      if (banner.active) {
        const start = banner.startDate ? new Date(banner.startDate) : null;
        const end = banner.endDate ? new Date(banner.endDate) : null;
        if (start && start > now) scheduleStatus = 'scheduled';
        else if (end && end < now) scheduleStatus = 'expired';
        else scheduleStatus = 'live';
      }
      return { ...banner, scheduleStatus };
    });
  }

  async function loadBanners() {
    const res = await fetch('/admin/api/banners');
    const data = await res.json();
    renderList(enrichBanners(data.banners || []));
  }

  function openModal(mode, banner) {
    form.reset();
    previewWrap.classList.remove('visible');
    previewImg.removeAttribute('src');
    imageInput.required = mode === 'create';

    bannerIdInput.value = banner ? banner.id : '';
    modalTitle.textContent = mode === 'create' ? 'Create Banner' : 'Edit Banner';

    if (banner) {
      form.elements.title.value = banner.title || '';
      form.elements.subtitle.value = banner.subtitle || '';
      form.elements.buttonText.value = banner.buttonText || '';
      form.elements.buttonLink.value = banner.buttonLink || '';
      form.elements.backgroundColor.value = banner.backgroundColor || '#f5f5f5';
      form.elements.startDate.value = banner.startDate || '';
      form.elements.endDate.value = banner.endDate || '';
      form.elements.active.checked = !!banner.active;
      if (banner.image) {
        previewImg.src = banner.image;
        previewWrap.classList.add('visible');
      }
    }

    modal.classList.add('open');
  }

  function closeModal() {
    modal.classList.remove('open');
    form.reset();
    previewWrap.classList.remove('visible');
  }

  function setPreview(file) {
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (event) => {
      previewImg.src = event.target.result;
      previewWrap.classList.add('visible');
    };
    reader.readAsDataURL(file);
  }

  uploadZone.addEventListener('click', () => imageInput.click());
  uploadZone.addEventListener('dragover', (event) => {
    event.preventDefault();
    uploadZone.classList.add('dragover');
  });
  uploadZone.addEventListener('dragleave', () => uploadZone.classList.remove('dragover'));
  uploadZone.addEventListener('drop', (event) => {
    event.preventDefault();
    uploadZone.classList.remove('dragover');
    const file = event.dataTransfer.files[0];
    if (file) {
      imageInput.files = event.dataTransfer.files;
      setPreview(file);
    }
  });
  imageInput.addEventListener('change', () => {
    if (imageInput.files[0]) setPreview(imageInput.files[0]);
  });

  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    const id = bannerIdInput.value;
    const url = id ? `/admin/api/banners/edit/${id}` : '/admin/api/banners/create';
    const body = new FormData(form);
    body.set('active', form.elements.active.checked ? 'true' : 'false');

    const res = await fetch(url, { method: 'POST', body });
    const data = await res.json();
    if (!res.ok) {
      showToast(data.error || 'Could not save banner', true);
      return;
    }

    showToast(id ? 'Banner updated' : 'Banner created');
    closeModal();
    await loadBanners();
  });

  async function onRowAction(event) {
    const btn = event.currentTarget;
    const id = btn.dataset.id;
    const action = btn.dataset.action;

    if (action === 'edit') {
      const banner = banners.find((item) => String(item.id) === String(id));
      openModal('edit', banner);
      return;
    }

    if (action === 'toggle') {
      const res = await fetch(`/admin/api/banners/toggle/${id}`, { method: 'POST' });
      const data = await res.json();
      if (!res.ok) {
        showToast(data.error || 'Could not toggle banner', true);
        return;
      }
      showToast('Banner status updated');
      await loadBanners();
      return;
    }

    if (action === 'delete') {
      if (!confirm('Delete this banner permanently?')) return;
      const res = await fetch(`/admin/api/banners/delete/${id}`, { method: 'POST' });
      const data = await res.json();
      if (!res.ok) {
        showToast(data.error || 'Could not delete banner', true);
        return;
      }
      showToast('Banner deleted');
      await loadBanners();
    }
  }

  document.getElementById('btn-create-banner')?.addEventListener('click', () => openModal('create'));
  document.getElementById('btn-close-modal')?.addEventListener('click', closeModal);
  modal?.addEventListener('click', (event) => {
    if (event.target === modal) closeModal();
  });

  const initial = window.__BANNERS_INITIAL__;
  if (initial && initial.length) {
    renderList(enrichBanners(initial));
  } else {
    loadBanners();
  }

  const params = new URLSearchParams(window.location.search);
  if (params.get('action') === 'create') openModal('create');
  const editId = params.get('edit');
  if (editId) {
    const banner = (initial || []).find((item) => String(item.id) === String(editId));
    if (banner) openModal('edit', banner);
    else {
      loadBanners().then(() => {
        const found = banners.find((item) => String(item.id) === String(editId));
        if (found) openModal('edit', found);
      });
    }
  }
})();
