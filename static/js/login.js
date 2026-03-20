    let isSignUpMode = false;

    function toggleAuthMode(e) {
        e.preventDefault();
        isSignUpMode = !isSignUpMode;

        const subtitle = document.getElementById('authSubtitle');
        const usernameField = document.getElementById('usernameField');
        const usernameInput = document.getElementById('usernameInput');
        const forgotPwd = document.getElementById('forgotPwdContainer');
        const submitBtn = document.getElementById('mainSubmitBtn');
        const guestBtn = document.getElementById('guestBtn');
        const togglePrefix = document.getElementById('togglePrefix');
        const toggleBtn = document.getElementById('toggleAuthBtn');
        const toggleContainer = document.getElementById('toggleTextContainer');

        // Smooth fade out
        subtitle.style.opacity = '0';
        submitBtn.style.opacity = '0';
        toggleContainer.style.opacity = '0';

        setTimeout(() => {
            if (isSignUpMode) {
                document.getElementById('authMode').value = "signup";
                subtitle.innerText = "Create your account";
                usernameField.style.display = 'block';
                setTimeout(() => { usernameField.style.opacity = '1'; }, 50);
                usernameInput.required = true;

                forgotPwd.style.display = 'none';
                guestBtn.style.display = 'none';

                submitBtn.innerText = "Sign Up";
                togglePrefix.innerText = "Already have an account?";
                toggleBtn.innerText = "Login";
            } else {
                document.getElementById('authMode').value = "login";
                subtitle.innerText = "Your path to success starts here";
                usernameField.style.opacity = '0';
                setTimeout(() => { usernameField.style.display = 'none'; }, 300);
                usernameInput.required = false;
                usernameInput.value = '';

                forgotPwd.style.display = 'block';
                guestBtn.style.display = 'block';

                submitBtn.innerText = "Login";
                togglePrefix.innerText = "Don't have an account?";
                toggleBtn.innerText = "Sign Up";
            }

            // Smooth fade in
            subtitle.style.opacity = '1';
            submitBtn.style.opacity = '1';
            toggleContainer.style.opacity = '1';
        }, 300);
    }

    function openForgotModal() {
        const modal = document.getElementById('forgotPwdModal');
        modal.classList.add('show');
        resetModalState();
        setTimeout(() => modal.classList.add('active'), 10);
    }

    function closeForgotModal() {
        const modal = document.getElementById('forgotPwdModal');
        modal.classList.remove('active');
        setTimeout(() => modal.classList.remove('show'), 300);
    }

    function resetModalState() {
        document.getElementById('fp-step-1').style.display = 'block';
        document.getElementById('fp-step-2').style.display = 'none';
        document.getElementById('fp-step-3').style.display = 'none';
        document.getElementById('fpEmail').value = '';
        document.getElementById('fpOtp').value = '';
        document.getElementById('fpNewPwd').value = '';
        document.getElementById('fpConfirmPwd').value = '';
        document.getElementById('fpError1').style.display = 'none';
        document.getElementById('fpError2').style.display = 'none';
        document.getElementById('fpError3').style.display = 'none';
        document.getElementById('fpSuccess').style.display = 'none';
    }

    async function sendOtp() {
        const email = document.getElementById('fpEmail').value;
        const err = document.getElementById('fpError1');
        if (!email) { err.textContent = "Please enter your email"; err.style.display = 'block'; return; }

        err.style.display = 'none';
        document.getElementById('sendOtpText').textContent = "Sending...";
        document.getElementById('sendOtpLoader').style.display = 'block';
        document.getElementById('btnSendOtp').disabled = true;

        try {
            const res = await fetch('/api/forgot-password/send-otp', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email })
            });
            const data = await res.json();

            document.getElementById('sendOtpText').textContent = "Send OTP";
            document.getElementById('sendOtpLoader').style.display = 'none';
            document.getElementById('btnSendOtp').disabled = false;

            if (res.ok) {
                if (data.status === "demo") {
                    alert("⚠️ DEMO MODE: You haven't configured a real email server in .env yet!\n\nYour 6-digit OTP for " + data.email + " is: " + data.otp);
                }
                document.getElementById('fp-step-1').style.display = 'none';
                document.getElementById('fp-step-2').style.display = 'block';
            } else {
                err.textContent = data.message;
                err.style.display = 'block';
            }
        } catch (e) {
            err.textContent = "Network Error";
            err.style.display = 'block';
        }
    }

    async function verifyOtp() {
        const otp = document.getElementById('fpOtp').value;
        const err = document.getElementById('fpError2');
        if (!otp || otp.length < 6) { err.textContent = "Please enter a valid 6-digit OTP"; err.style.display = 'block'; return; }

        err.style.display = 'none';
        try {
            const res = await fetch('/api/forgot-password/verify-otp', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ otp })
            });
            const data = await res.json();

            if (res.ok) {
                document.getElementById('fp-step-2').style.display = 'none';
                document.getElementById('fp-step-3').style.display = 'block';
            } else {
                err.textContent = data.message;
                err.style.display = 'block';
            }
        } catch (e) {
            err.textContent = "Network Error";
            err.style.display = 'block';
        }
    }

    async function resetPassword() {
        const newPwd = document.getElementById('fpNewPwd').value;
        const confPwd = document.getElementById('fpConfirmPwd').value;
        const err = document.getElementById('fpError3');
        const success = document.getElementById('fpSuccess');

        if (!newPwd || newPwd !== confPwd) {
            err.textContent = "Passwords do not match!";
            err.style.display = 'block';
            return;
        }

        err.style.display = 'none';
        try {
            const res = await fetch('/api/forgot-password/reset', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ new_password: newPwd })
            });
            const data = await res.json();

            if (res.ok) {
                success.textContent = "Password smoothly reset! Please close and Login.";
                success.style.display = 'block';
                setTimeout(() => closeForgotModal(), 3000);
            } else {
                err.textContent = data.message;
                err.style.display = 'block';
            }
        } catch (e) {
            err.textContent = "Network Error";
            err.style.display = 'block';
        }
    }
