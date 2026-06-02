(function () {
  function postJson(url, payload) {
    return fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
      body: JSON.stringify(payload),
      credentials: 'same-origin',
    }).then((res) =>
      res.json().then((data) => ({ ok: res.ok, status: res.status, data }))
    );
  }

  function setMessage(el, text, isError) {
    if (!el) return;
    el.textContent = text || '';
    el.classList.toggle('show', Boolean(text));
    el.classList.toggle('alert-success', Boolean(text) && !isError);
    el.classList.toggle('alert-error', Boolean(text) && isError);
  }

  function startCooldown(button, seconds) {
    if (!button) return;
    let remaining = seconds;
    const original = button.dataset.originalLabel || button.textContent;
    button.dataset.originalLabel = original;
    button.disabled = true;
    const tick = () => {
      if (remaining <= 0) {
        button.disabled = false;
        button.textContent = original;
        return;
      }
      button.textContent = `Resend in ${remaining}s`;
      remaining -= 1;
      setTimeout(tick, 1000);
    };
    tick();
  }

  window.initAuthOtp = function (config) {
    const sendBtn = document.getElementById(config.sendButtonId);
    const verifyBtn = document.getElementById(config.verifyButtonId);
    const emailInput = document.getElementById(config.emailInputId);
    const otpInput = document.getElementById(config.otpInputId);
    const messageEl = document.getElementById(config.messageId);
    const roleInput = config.roleInputId
      ? document.getElementById(config.roleInputId)
      : null;
    const purpose = config.purpose || 'login';

    if (sendBtn) {
      sendBtn.addEventListener('click', async (e) => {
        e.preventDefault();
        const email = (emailInput?.value || '').trim();
        if (!email) {
          setMessage(messageEl, 'Enter your email address first.', true);
          emailInput?.classList.add('error');
          return;
        }
        emailInput?.classList.remove('error');
        sendBtn.disabled = true;
        setMessage(messageEl, 'Sending code…', false);

        try {
          const { ok, data } = await postJson(config.sendUrl, {
            email,
            purpose,
          });
          if (!ok) {
            setMessage(messageEl, data.error || 'Could not send code.', true);
            sendBtn.disabled = false;
            return;
          }
          setMessage(messageEl, data.message || 'Code sent.', false);
          otpInput?.focus();
          startCooldown(sendBtn, 60);
        } catch {
          setMessage(messageEl, 'Network error. Try again.', true);
          sendBtn.disabled = false;
        }
      });
    }

    if (verifyBtn) {
      verifyBtn.addEventListener('click', async (e) => {
        e.preventDefault();
        const email = (emailInput?.value || '').trim();
        const otp = (otpInput?.value || '').trim();
        const role = roleInput?.value || 'customer';

        if (!email || !otp) {
          setMessage(messageEl, 'Enter email and verification code.', true);
          return;
        }

        verifyBtn.disabled = true;
        setMessage(messageEl, 'Verifying…', false);

        try {
          const { ok, data } = await postJson(config.verifyUrl, {
            email,
            otp,
            role,
          });
          if (!ok) {
            setMessage(messageEl, data.error || 'Verification failed.', true);
            verifyBtn.disabled = false;
            return;
          }
          window.location.href = data.redirect || '/';
        } catch {
          setMessage(messageEl, 'Network error. Try again.', true);
          verifyBtn.disabled = false;
        }
      });
    }
  };
})();
