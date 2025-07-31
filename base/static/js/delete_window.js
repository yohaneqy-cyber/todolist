document.addEventListener('DOMContentLoaded', () => {
  const deleteModal = document.getElementById('deleteModal');
  const cancelDeleteBtn = document.getElementById('cancelBtn');
  const modalTaskTitle = document.getElementById('modalTaskTitle');
  const deleteForm = document.getElementById('deleteForm');

  // Function to open modal with task title and form action URL
  function openDeleteModal(taskTitle, formActionUrl) {
    modalTaskTitle.textContent = taskTitle;
    deleteForm.setAttribute('action', formActionUrl);
    deleteModal.style.display = 'flex';
    document.body.style.overflow = 'hidden';  // prevent background scroll
  }

  // Function to close modal
  function closeDeleteModal() {
    deleteModal.style.display = 'none';
    document.body.style.overflow = '';
  }

  // Cancel button closes modal
  cancelDeleteBtn.addEventListener('click', closeDeleteModal);

  // Attach click to all delete buttons
  document.querySelectorAll('.delete-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const title = btn.getAttribute('data-title');
      const url = btn.getAttribute('data-url');
      openDeleteModal(title, url);
    });
  });

  // Optional: close modal if clicking outside modal content
  deleteModal.addEventListener('click', (e) => {
    if (e.target === deleteModal) {
      closeDeleteModal();
    }
  });
});