let isSignUpMode = false;

function byId(id) {
    return document.getElementById(id);
}

function setVisible(element, visible, displayValue = '') {
    if (!element) return;
    element.style.display = visible ? displayValue : 'none';
}

function setMessage(element, message) {
    if (!element) return;
    element.textContent = message;
    element.style.display = message ? 'block' : 'none';
}

function toggleAuthMode(e) {
    if (e) e.preventDefault();
    isSignUpMode = !isSignUpMode;

    const title = byId('authTitle');
    const subtitle = byId('authSubtitle');
    const usernameField = byId('usernameField');
    const usernameInput = byId('usernameInput');
    const forgotPwd = byId('forgotPwdContainer');
    const submitBtn = byId('mainSubmitBtn');
    const guestForm = byId('guestForm');
    const guestBtn = byId('guestBtn');
    const togglePrefix = byId('togglePrefix');
    const toggleBtn = byId('toggleAuthBtn');
    const toggleContainer = byId('toggleTextContainer');
    const authMode = byId('authMode');

    [subtitle, submitBtn, toggleContainer].forEach((element) => {
        if (element) element.style.opacity = '0';
    });

    window.setTimeout(() => {
        if (isSignUpMode) {
            if (authMode) authMode.value = 'signup';
            if (title) title.innerText = 'Create Account';
            if (subtitle) subtitle.innerText = 'Start a guided workspace for your career plan.';
            if (usernameField) {
                usernameField.style.display = 'grid';
                usernameField.setAttribute('aria-hidden', 'false');
                window.requestAnimationFrame(() => {
                    usernameField.style.opacity = '1';
                });
            }
            if (usernameInput) usernameInput.required = true;
            setVisible(forgotPwd, false);
            setVisible(guestForm, false);
            setVisible(guestBtn, false);
            if (submitBtn) submitBtn.innerText = 'Create Account';
            if (togglePrefix) togglePrefix.innerText = 'Already have an account?';
            if (toggleBtn) toggleBtn.innerText = 'Sign In';
        } else {
            if (authMode) authMode.value = 'login';
            if (title) title.innerText = 'Welcome Back';
            if (subtitle) subtitle.innerText = 'Log in to continue your roadmap, resume prep, and interview practice.';
            if (usernameField) {
                usernameField.style.opacity = '0';
                usernameField.setAttribute('aria-hidden', 'true');
                window.setTimeout(() => {
                    if (!isSignUpMode) usernameField.style.display = 'none';
                }, 180);
            }
            if (usernameInput) {
                usernameInput.required = false;
                usernameInput.value = '';
            }
            setVisible(forgotPwd, true);
            setVisible(guestForm, true);
            setVisible(guestBtn, true);
            if (submitBtn) submitBtn.innerText = 'Sign In';
            if (togglePrefix) togglePrefix.innerText = 'New to the platform?';
            if (toggleBtn) toggleBtn.innerText = 'Create Account';
        }

        [subtitle, submitBtn, toggleContainer].forEach((element) => {
            if (element) element.style.opacity = '1';
        });
    }, 180);
}

function openForgotModal() {
    const modal = byId('forgotPwdModal');
    if (!modal) return;

    resetModalState();
    modal.classList.add('show');
    modal.setAttribute('aria-hidden', 'false');
    document.body.classList.add('modal-open');

    window.requestAnimationFrame(() => {
        modal.classList.add('active');
        const emailInput = byId('fpEmail');
        if (emailInput) emailInput.focus();
    });
}

function closeForgotModal() {
    const modal = byId('forgotPwdModal');
    if (!modal) return;

    modal.classList.remove('active');
    modal.setAttribute('aria-hidden', 'true');
    document.body.classList.remove('modal-open');

    window.setTimeout(() => {
        modal.classList.remove('show');
    }, 180);
}

function resetModalState() {
    setVisible(byId('fp-step-1'), true, 'grid');
    setVisible(byId('fp-step-2'), false);
    setVisible(byId('fp-step-3'), false);

    ['fpEmail', 'fpOtp', 'fpNewPwd', 'fpConfirmPwd'].forEach((id) => {
        const field = byId(id);
        if (field) field.value = '';
    });

    ['fpError1', 'fpError2', 'fpError3', 'fpSuccess'].forEach((id) => {
        setMessage(byId(id), '');
    });

    const sendOtpText = byId('sendOtpText');
    const sendOtpLoader = byId('sendOtpLoader');
    const sendOtpButton = byId('btnSendOtp');
    if (sendOtpText) sendOtpText.textContent = 'Send OTP';
    if (sendOtpLoader) sendOtpLoader.style.display = 'none';
    if (sendOtpButton) sendOtpButton.disabled = false;
}

async function sendOtp() {
    const emailInput = byId('fpEmail');
    const email = emailInput ? emailInput.value.trim() : '';
    const err = byId('fpError1');

    if (!email) {
        setMessage(err, 'Please enter your email');
        return;
    }

    setMessage(err, '');
    const sendOtpText = byId('sendOtpText');
    const sendOtpLoader = byId('sendOtpLoader');
    const sendOtpButton = byId('btnSendOtp');
    if (sendOtpText) sendOtpText.textContent = 'Sending...';
    if (sendOtpLoader) sendOtpLoader.style.display = 'inline-block';
    if (sendOtpButton) sendOtpButton.disabled = true;

    try {
        const res = await fetch('/api/forgot-password/send-otp', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email })
        });
        const data = await res.json();

        if (sendOtpText) sendOtpText.textContent = 'Send OTP';
        if (sendOtpLoader) sendOtpLoader.style.display = 'none';
        if (sendOtpButton) sendOtpButton.disabled = false;

        if (res.ok) {
            if (data.status === 'demo') {
                alert('DEMO MODE: Email server is not configured yet.\n\nYour 6-digit OTP for ' + data.email + ' is: ' + data.otp);
            }
            setVisible(byId('fp-step-1'), false);
            setVisible(byId('fp-step-2'), true, 'grid');
            const otpInput = byId('fpOtp');
            if (otpInput) otpInput.focus();
        } else {
            setMessage(err, data.message || 'Unable to send OTP. Please try again.');
        }
    } catch (error) {
        if (sendOtpText) sendOtpText.textContent = 'Send OTP';
        if (sendOtpLoader) sendOtpLoader.style.display = 'none';
        if (sendOtpButton) sendOtpButton.disabled = false;
        setMessage(err, 'Network error. Please try again.');
    }
}

async function verifyOtp() {
    const otpInput = byId('fpOtp');
    const otp = otpInput ? otpInput.value.trim() : '';
    const err = byId('fpError2');

    if (!otp || otp.length < 6) {
        setMessage(err, 'Please enter a valid 6-digit OTP');
        return;
    }

    setMessage(err, '');
    try {
        const res = await fetch('/api/forgot-password/verify-otp', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ otp })
        });
        const data = await res.json();

        if (res.ok) {
            setVisible(byId('fp-step-2'), false);
            setVisible(byId('fp-step-3'), true, 'grid');
            const newPassword = byId('fpNewPwd');
            if (newPassword) newPassword.focus();
        } else {
            setMessage(err, data.message || 'Invalid OTP. Please try again.');
        }
    } catch (error) {
        setMessage(err, 'Network error. Please try again.');
    }
}

async function resetPassword() {
    const newPasswordInput = byId('fpNewPwd');
    const confirmPasswordInput = byId('fpConfirmPwd');
    const newPwd = newPasswordInput ? newPasswordInput.value : '';
    const confPwd = confirmPasswordInput ? confirmPasswordInput.value : '';
    const err = byId('fpError3');
    const success = byId('fpSuccess');

    if (!newPwd || newPwd !== confPwd) {
        setMessage(success, '');
        setMessage(err, 'Passwords do not match.');
        return;
    }

    setMessage(err, '');
    try {
        const res = await fetch('/api/forgot-password/reset', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ new_password: newPwd })
        });
        const data = await res.json();

        if (res.ok) {
            setMessage(success, 'Password reset complete. Please sign in.');
            window.setTimeout(() => closeForgotModal(), 2400);
        } else {
            setMessage(success, '');
            setMessage(err, data.message || 'Unable to reset password. Please try again.');
        }
    } catch (error) {
        setMessage(success, '');
        setMessage(err, 'Network error. Please try again.');
    }
}

document.addEventListener('DOMContentLoaded', () => {
    const modal = byId('forgotPwdModal');
    if (modal) {
        modal.addEventListener('click', (event) => {
            if (event.target === modal) closeForgotModal();
        });
    }

    document.addEventListener('keydown', (event) => {
        if (event.key === 'Escape' && modal && modal.classList.contains('show')) {
            closeForgotModal();
        }
    });
});
