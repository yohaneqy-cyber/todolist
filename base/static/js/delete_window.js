document.addEventListener("DOMContentLoaded", function() {
  const deleteButtons = document.querySelectorAll(".delete-btn");
  const deleteModal = document.getElementById("deleteModal");
  const modalTaskTitle = document.getElementById("modalTaskTitle");
  const deleteForm = document.getElementById("deleteForm");
  const cancelBtn = document.getElementById("cancelBtn");

  deleteButtons.forEach(btn => {
    btn.addEventListener("click", function() {
      const taskTitle = btn.getAttribute("data-title");
      const actionUrl = btn.getAttribute("data-url");

      if (!actionUrl) {
        alert("آدرس حذف تعیین نشده است!");
        return;
      }

      modalTaskTitle.textContent = taskTitle;
      deleteForm.action = actionUrl;
      deleteModal.style.display = "flex";  // چون در CSS از display:flex برای مرکزچین کردن استفاده کردی
    });
  });

  cancelBtn.addEventListener("click", function() {
    deleteModal.style.display = "none";
  });

  window.addEventListener("click", function(event) {
    if (event.target === deleteModal) {
      deleteModal.style.display = "none";
    }
  });
});
