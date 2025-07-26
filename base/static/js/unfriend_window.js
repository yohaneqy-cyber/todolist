// unfriend.js

document.addEventListener('DOMContentLoaded', () => {
  const confirmUnfriendModal = document.getElementById("confirmUnfriendModal");
  const closeConfirmUnfriendModal = document.getElementById("closeConfirmUnfriendModal");
  const confirmUnfriendBtn = document.getElementById("confirmUnfriendBtn");
  const cancelUnfriendBtn = document.getElementById("cancelUnfriendBtn");

  let friendToRemoveId = null;

  // فرض می‌کنیم دکمه‌های "Unfriend" در صفحه با کلاس 'unfriend-btn' هستند
  document.querySelectorAll('.unfriend-btn').forEach(button => {
    button.addEventListener('click', () => {
      friendToRemoveId = button.dataset.userid;  // فرض می‌کنیم آی‌دی کاربر در data-userid هست
      confirmUnfriendModal.style.display = "flex";
      confirmUnfriendModal.setAttribute('aria-hidden', 'false');
    });
  });

  // بستن مودال با کلیک روی Cancel یا Close
  const closeModal = () => {
    confirmUnfriendModal.style.display = "none";
    confirmUnfriendModal.setAttribute('aria-hidden', 'true');
    friendToRemoveId = null;
  };

  closeConfirmUnfriendModal.addEventListener('click', closeModal);
  cancelUnfriendBtn.addEventListener('click', closeModal);

  // تایید حذف دوست
  confirmUnfriendBtn.addEventListener('click', () => {
    if (!friendToRemoveId) return;
    fetch(`/unfriend/${friendToRemoveId}/`, {
      method: "POST",
      headers: {
        "X-CSRFToken": getCSRFToken(), // تابع getCSRFToken باید در همین فایل یا از فایل مشترک لود شده باشد
        "X-Requested-With": "XMLHttpRequest"
      }
    })
    .then(res => res.json())
    .then(data => {
      if (data.success) {
        closeModal();
        // اینجا می‌تونی لیست دوستان رو رفرش کنی یا آیتم حذف شده رو از DOM پاک کنی
        location.reload();  // ساده‌ترین راه: رفرش صفحه
      } else {
        alert(data.error || "Failed to unfriend.");
      }
    })
    .catch(() => alert("Network error, please try again."));
  });
});

// اگر getCSRFToken در فایل جدا هست، یا اینجا تعریفش کن، یا اطمینان حاصل کن که قبل این فایل بارگذاری شده باشد
function getCSRFToken() {
  let cookieValue = null;
  if (document.cookie && document.cookie !== '') {
    const cookies = document.cookie.split(';');
    for (let cookie of cookies) {
      cookie = cookie.trim();
      if (cookie.startsWith('csrftoken=')) {
        cookieValue = decodeURIComponent(cookie.substring('csrftoken='.length));
        break;
      }
    }
  }
  return cookieValue;
}
