const deleteModal = document.getElementById('deleteModal');
const cancelDeleteBtn = document.getElementById('cancelBtn');

// باز کردن مودال (مثلاً از یه دکمه خارجی)
function openDeleteModal(taskTitle, formActionUrl) {
  const modalTitle = document.getElementById('modalTaskTitle');
  const form = document.getElementById('deleteForm');

  modalTitle.textContent = taskTitle;
  form.setAttribute('action', formActionUrl);

  deleteModal.classList.remove('hide');
  deleteModal.classList.add('show');
  deleteModal.style.display = 'flex';
  document.body.classList.add('modal-open');
}

// بستن مودال
function closeDeleteModal() {
  deleteModal.classList.remove('show');
  deleteModal.classList.add('hide');
  document.body.classList.remove('modal-open');

  deleteModal.addEventListener('animationend', () => {
    if (deleteModal.classList.contains('hide')) {
      deleteModal.style.display = 'none';
      deleteModal.classList.remove('hide');
    }
  }, { once: true });
}

// دکمه کنسل
cancelDeleteBtn.addEventListener('click', closeDeleteModal);
