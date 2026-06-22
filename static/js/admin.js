/**
 * admin.js — Lead Dashboard interactivity
 * Handles: status updates, search/filter, polling for live updates, detail modal
 */

'use strict';

const $  = (sel, ctx = document) => ctx.querySelector(sel);
const $$ = (sel, ctx = document) => [...ctx.querySelectorAll(sel)];

const tableBody    = $('#leadsTableBody');
const leadsEmpty    = $('#leadsEmpty');
const searchInput   = $('#searchInput');
const statusFilters = $('#statusFilters');

let currentStatus = (statusFilters && $('.filter-btn.active', statusFilters)?.dataset.status) || 'All';
let currentSearch = searchInput ? searchInput.value : '';
let knownIds      = new Set();
let pollTimer     = null;
let searchDebounce = null;

/* ═══════════════════════════════════════════════════════
   INIT — capture currently rendered lead IDs
═══════════════════════════════════════════════════════ */
function captureKnownIds() {
  knownIds = new Set($$('.lead-row').map(r => r.dataset.id));
}
captureKnownIds();

/* ═══════════════════════════════════════════════════════
   FETCH & RENDER LEADS
═══════════════════════════════════════════════════════ */
async function fetchLeads(isPoll = false) {
  const params = new URLSearchParams({ status: currentStatus, q: currentSearch });
  try {
    const resp = await fetch(`/admin/api/leads?${params.toString()}`);
    if (!resp.ok) return;
    const data = await resp.json();
    renderLeads(data.leads, isPoll);
    renderStats(data.stats);
  } catch (err) {
    console.error('Failed to fetch leads', err);
  }
}

function renderStats(stats) {
  $('#statTotal').textContent     = stats.total;
  $('#statNew').textContent       = stats.new;
  $('#statContacted').textContent = stats.contacted;
  $('#statWon').textContent       = stats.won;
  $('#statLost').textContent      = stats.lost;
}

function renderLeads(leads, isPoll) {
  if (!leads.length) {
    tableBody.innerHTML = '';
    leadsEmpty.style.display = 'block';
    knownIds = new Set();
    return;
  }
  leadsEmpty.style.display = 'none';

  const newIds = new Set(leads.map(l => String(l.id)));
  const isFreshLead = isPoll && [...newIds].some(id => !knownIds.has(id));

  tableBody.innerHTML = leads.map(rowHTML).join('');
  attachRowHandlers();

  if (isFreshLead) {
    // Flash the newest row(s) that weren't present before
    leads.forEach(l => {
      if (!knownIds.has(String(l.id))) {
        const row = tableBody.querySelector(`tr[data-id="${l.id}"]`);
        if (row) row.classList.add('lead-row--flash');
      }
    });
  }

  knownIds = newIds;
}

function rowHTML(lead) {
  const statusLower = lead.status.toLowerCase();
  const dateDisplay = lead.created_at.replace('T', ' ');
  return `
    <tr class="lead-row" data-id="${lead.id}">
      <td>
        <div class="lead-name">${escapeHTML(lead.name)}</div>
        ${lead.business ? `<div class="lead-business">${escapeHTML(lead.business)}</div>` : ''}
      </td>
      <td>
        <div class="lead-email">${escapeHTML(lead.email)}</div>
        ${lead.phone ? `<div class="lead-phone">${escapeHTML(lead.phone)}</div>` : ''}
      </td>
      <td><span class="lead-service">${escapeHTML(lead.service_type) || '—'}</span></td>
      <td><span class="lead-budget">${escapeHTML(lead.budget) || '—'}</span></td>
      <td><span class="lead-date">${dateDisplay}</span></td>
      <td>
        <select class="status-select status-${statusLower}" data-id="${lead.id}">
          <option value="New" ${lead.status === 'New' ? 'selected' : ''}>New</option>
          <option value="Contacted" ${lead.status === 'Contacted' ? 'selected' : ''}>Contacted</option>
          <option value="Won" ${lead.status === 'Won' ? 'selected' : ''}>Won</option>
          <option value="Lost" ${lead.status === 'Lost' ? 'selected' : ''}>Lost</option>
        </select>
      </td>
      <td><button class="lead-view-btn" data-id="${lead.id}" title="View details"><i class="fas fa-eye"></i></button></td>
    </tr>`;
}

function escapeHTML(str) {
  if (!str) return '';
  const div = document.createElement('div');
  div.textContent = str;
  return div.innerHTML;
}

/* ═══════════════════════════════════════════════════════
   ROW EVENT HANDLERS (status select + view button)
═══════════════════════════════════════════════════════ */
function attachRowHandlers() {
  $$('.status-select').forEach(sel => {
    sel.addEventListener('change', onStatusChange);
  });
  $$('.lead-view-btn').forEach(btn => {
    btn.addEventListener('click', () => openLeadModal(btn.dataset.id));
  });
}
attachRowHandlers();

async function onStatusChange(e) {
  const select = e.target;
  const id     = select.dataset.id;
  const status = select.value;

  select.className = `status-select status-${status.toLowerCase()}`;

  try {
    const resp = await fetch(`/admin/api/leads/${id}/status`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ status }),
    });
    const data = await resp.json();
    if (data.success) {
      fetchLeads(); // refresh stats
    }
  } catch (err) {
    console.error('Failed to update status', err);
  }
}

/* ═══════════════════════════════════════════════════════
   FILTERS — status buttons + search
═══════════════════════════════════════════════════════ */
if (statusFilters) {
  $$('.filter-btn', statusFilters).forEach(btn => {
    btn.addEventListener('click', () => {
      $$('.filter-btn', statusFilters).forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      currentStatus = btn.dataset.status;
      fetchLeads();
    });
  });
}

if (searchInput) {
  searchInput.addEventListener('input', () => {
    clearTimeout(searchDebounce);
    searchDebounce = setTimeout(() => {
      currentSearch = searchInput.value.trim();
      fetchLeads();
    }, 350);
  });
}

/* ═══════════════════════════════════════════════════════
   LEAD DETAIL MODAL
═══════════════════════════════════════════════════════ */
const leadModal     = $('#leadModal');
const leadModalBody = $('#leadModalBody');
const leadModalClose = $('#leadModalClose');

async function openLeadModal(id) {
  const params = new URLSearchParams({ status: 'All', q: '' });
  try {
    const resp = await fetch(`/admin/api/leads?${params.toString()}`);
    const data = await resp.json();
    const lead = data.leads.find(l => String(l.id) === String(id));
    if (!lead) return;

    leadModalBody.innerHTML = `
      <div class="lead-detail-header">
        <div>
          <h2>${escapeHTML(lead.name)}</h2>
          <p style="margin:0;color:var(--grey-3);font-size:.85rem;">${lead.created_at.replace('T',' ')}</p>
        </div>
        <select class="status-select status-${lead.status.toLowerCase()}" data-id="${lead.id}" id="modalStatusSelect">
          <option value="New" ${lead.status === 'New' ? 'selected' : ''}>New</option>
          <option value="Contacted" ${lead.status === 'Contacted' ? 'selected' : ''}>Contacted</option>
          <option value="Won" ${lead.status === 'Won' ? 'selected' : ''}>Won</option>
          <option value="Lost" ${lead.status === 'Lost' ? 'selected' : ''}>Lost</option>
        </select>
      </div>

      <div class="lead-detail-grid">
        <div class="lead-detail-item"><label>Email</label><div><a href="mailto:${escapeHTML(lead.email)}" style="color:var(--indigo-glow)">${escapeHTML(lead.email)}</a></div></div>
        <div class="lead-detail-item"><label>Phone</label><div>${escapeHTML(lead.phone) || '—'}</div></div>
        <div class="lead-detail-item"><label>Business</label><div>${escapeHTML(lead.business) || '—'}</div></div>
        <div class="lead-detail-item"><label>Service</label><div>${escapeHTML(lead.service_type) || '—'}</div></div>
        <div class="lead-detail-item"><label>Budget</label><div>${escapeHTML(lead.budget) || '—'}</div></div>
      </div>

      <label style="display:block;font-size:.72rem;text-transform:uppercase;letter-spacing:.06em;color:var(--grey-3);margin-bottom:6px;">Project Details</label>
      <div class="lead-detail-message">${escapeHTML(lead.message)}</div>

      <label style="display:block;font-size:.72rem;text-transform:uppercase;letter-spacing:.06em;color:var(--grey-3);margin-bottom:6px;">Internal Notes</label>
      <textarea class="lead-notes-area" id="modalNotesArea" placeholder="Add private notes about this lead...">${escapeHTML(lead.notes)}</textarea>

      <div class="lead-detail-actions" style="margin-top:20px;">
        <a href="https://wa.me/91${(lead.phone || '').replace(/\\D/g,'')}" target="_blank" class="btn btn-whatsapp btn-sm"><i class="fab fa-whatsapp"></i> WhatsApp</a>
        <a href="mailto:${escapeHTML(lead.email)}" class="btn btn-outline btn-sm"><i class="fas fa-envelope"></i> Email</a>
        <button class="btn btn-primary btn-sm" id="saveNotesBtn"><i class="fas fa-save"></i> Save Notes</button>
        <button class="btn btn-danger btn-sm" id="deleteLeadBtn" data-id="${lead.id}"><i class="fas fa-trash"></i> Delete</button>
      </div>
    `;

    $('#modalStatusSelect').addEventListener('change', onStatusChange);
    $('#saveNotesBtn').addEventListener('click', () => saveNotes(lead.id));
    $('#deleteLeadBtn').addEventListener('click', () => deleteLead(lead.id));

    leadModal.classList.add('active');
    document.body.style.overflow = 'hidden';
  } catch (err) {
    console.error('Failed to load lead detail', err);
  }
}

async function saveNotes(id) {
  const notes = $('#modalNotesArea').value;
  const btn = $('#saveNotesBtn');
  btn.disabled = true;
  btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Saving...';
  try {
    await fetch(`/admin/api/leads/${id}/notes`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ notes }),
    });
    btn.innerHTML = '<i class="fas fa-check"></i> Saved';
    setTimeout(() => { btn.innerHTML = '<i class="fas fa-save"></i> Save Notes'; btn.disabled = false; }, 1500);
  } catch (err) {
    btn.innerHTML = '<i class="fas fa-save"></i> Save Notes';
    btn.disabled = false;
  }
}

async function deleteLead(id) {
  if (!confirm('Delete this lead permanently? This cannot be undone.')) return;
  try {
    const resp = await fetch(`/admin/api/leads/${id}/delete`, { method: 'POST' });
    const data = await resp.json();
    if (data.success) {
      closeModal();
      fetchLeads();
    }
  } catch (err) {
    console.error('Failed to delete lead', err);
  }
}

function closeModal() {
  leadModal.classList.remove('active');
  document.body.style.overflow = '';
}

if (leadModalClose) leadModalClose.addEventListener('click', closeModal);
if (leadModal) {
  leadModal.addEventListener('click', e => { if (e.target === leadModal) closeModal(); });
}
document.addEventListener('keydown', e => { if (e.key === 'Escape') closeModal(); });

/* ═══════════════════════════════════════════════════════
   POLLING — near-real-time updates every 8 seconds
═══════════════════════════════════════════════════════ */
function startPolling() {
  pollTimer = setInterval(() => fetchLeads(true), 8000);
}
function stopPolling() {
  if (pollTimer) clearInterval(pollTimer);
}

// Pause polling when tab is hidden to save resources; resume when visible
document.addEventListener('visibilitychange', () => {
  if (document.hidden) {
    stopPolling();
  } else {
    fetchLeads(true);
    startPolling();
  }
});

startPolling();

console.log('%c✦ Admin Dashboard Active', 'color:#818CF8;font-size:13px;font-weight:bold;');
