function hideErrorSmooth(error, duration = 400) {
  error.classList.add('hide');
  setTimeout(() => {
    if (error.parentNode) error.parentNode.removeChild(error);
  }, duration);
}

function hideErrorsSequentially(selector, initialDelay = 4000, delayBetween = 300) {
  const errors = document.querySelectorAll(selector);
  errors.forEach((error, i) => {
    setTimeout(() => {
      hideErrorSmooth(error);
    }, initialDelay + i * delayBetween);
  });
}

document.addEventListener('DOMContentLoaded', () => {
  hideErrorsSequentially('.error-message', 4000, 350);
});
document.addEventListener('DOMContentLoaded', () => {
  const focusableElements = Array.from(document.querySelectorAll('input, textarea, select, button'));

  focusableElements.forEach((el, i) => {
    el.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') {
        e.preventDefault();

        const nextEl = focusableElements[i + 1];
        if (!nextEl) return;

        const tag = nextEl.tagName.toLowerCase();

        if (tag === 'button' || (tag === 'input' && nextEl.type === 'submit')) {
          // اگر submit بود فرم رو ارسال کن
          if (nextEl.type === 'submit') {
            const form = nextEl.closest('form');
            if (form) {
              form.requestSubmit ? form.requestSubmit() : form.submit();
              return;
            }
          }

          // کلیک شبیه‌سازی
          const event = new MouseEvent('click', {
            view: window,
            bubbles: true,
            cancelable: true
          });
          nextEl.dispatchEvent(event);
        } else {
          nextEl.focus();
        }
      }
    });
  });
});

function hideErrorSmooth(error, delay = 400) {
  error.classList.add('hide');
  setTimeout(() => {
    if (error.parentNode) {
      error.remove();
    }
  }, 500); // Match with CSS transition time (0.5s)
}

function hideErrorsSequentially(selector, initialDelay = 4000, delayBetween = 300) {
  const errors = document.querySelectorAll(selector);
  errors.forEach((error, i) => {
    setTimeout(() => {
      hideErrorSmooth(error);
    }, initialDelay + i * delayBetween);
  });
}

document.addEventListener('DOMContentLoaded', () => {
  hideErrorsSequentially('.error-message', 3000, 250);
});

document.addEventListener('DOMContentLoaded', () => {
  const inputs = document.querySelectorAll('input.login-input');

  function enforceDarkStyle(input) {
    input.style.backgroundColor = '#1f1f1f';
    input.style.color = '#e0e0e0';
    input.style.caretColor = '#e0e0e0';
    input.style.borderColor = '#444';
  }

  inputs.forEach(input => {
    enforceDarkStyle(input);

    // روی focus, input, change و blur مجدد اعمال کن
    input.addEventListener('focus', () => enforceDarkStyle(input));
    input.addEventListener('input', () => enforceDarkStyle(input));
    input.addEventListener('change', () => enforceDarkStyle(input));
    input.addEventListener('blur', () => enforceDarkStyle(input));
  });

  // اگه autofill باعث تغییرات DOM شد دوباره اعمال کن
  const observer = new MutationObserver(() => {
    inputs.forEach(input => enforceDarkStyle(input));
  });

  inputs.forEach(input => {
    observer.observe(input, { attributes: true, attributeFilter: ['style', 'class'] });
  });

  // به صورت دوره‌ای هر 500 میلی‌ثانیه اجرا کن تا تغییر رنگی نداشته باشیم
  setInterval(() => {
    inputs.forEach(input => enforceDarkStyle(input));
  }, 500);
});
